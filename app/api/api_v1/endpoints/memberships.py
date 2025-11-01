from typing import List, Optional
from fastapi import APIRouter, Depends, Header, status, Response, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.testing.suite.test_reflection import metadata

from app.db.session import get_db
from app.schemas.responses import DataResponse
from app.schemas.membership import MembershipPlan, CompanyMembershipCreate
from app.services.crud import membership as crud_membership
from app.api.dependencies import require_admin_or_owner, get_current_company_id
from app.core.config import settings
import stripe
import json

router = APIRouter()

stripe.api_key = settings.STRIPE_API_KEY
endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

@router.get("/plans", response_model=DataResponse[List[MembershipPlan]])
async def list_membership_plans(
    *,
    db: Session = Depends(get_db),
    # Only owners and admins can list plans
    _role = Depends(require_admin_or_owner),
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True
) -> DataResponse:
    """
    List membership plans. Requires admin or owner.
    """
    plans = crud_membership.membership_plan.get_all(db, skip=skip, limit=limit, active_only=active_only)
    return DataResponse.success_response(
        data=plans,
        message="Membership plans fetched successfully"
    )


@router.post("/create-checkout-session/{membership_plan_id}")
async def create_checkout_session(membership_plan_id: str,
                                  db: Session = Depends(get_db),
                                  company_id=Depends(get_current_company_id),
                                  _role=Depends(require_admin_or_owner)):

    membership_plan = crud_membership.membership_plan.get(db, id=membership_plan_id)
    if not membership_plan:
        raise HTTPException(status_code=404, detail="Membership plan not found")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price": membership_plan.url,
                "quantity": 1,
            }],
            success_url=f"{settings.API_URL}/api/v1/memberships/webhook",
            cancel_url=f"{settings.API_URL}/api/v1/memberships/cancel",
            ui_mode="hosted",
            subscription_data={
                'billing_mode': {
                    'type': 'flexible'
                }
            },
            metadata={
                'company_id': company_id,
                'plan_id': membership_plan_id
            }
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/webhook/subscription")
async def webhook_subscription(request: Request,
                               db: Session = Depends(get_db), ):
    try:
        payload = await request.body()
    except Exception as e:
        print("⚠️  Error getting request body:", e)
        raise HTTPException(status_code=400, detail="Invalid payload")

    signature = request.headers.get("stripe-signature")
    print("signature: ", signature)

    # Verify Stripe signature if secret is set
    if endpoint_secret:
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature,
                secret=endpoint_secret
            )
            print("Webhook signature verification succeeded")
        except stripe.error.SignatureVerificationError as e:
            print("⚠️  Webhook signature verification failed:", e)
            return JSONResponse(content={"success": False}, status_code=400)
    else:
        event = await request.json()

    print(f'event_type: {event["type"]}')
    # Handle different event types
    if event["type"] == "checkout.session.completed":
        payment_intent = event["data"]["object"]
        print(f"payment_intent: {payment_intent}")
        print(f"💰 Payment for {payment_intent['amount_total']} succeeded.")
        # handle_payment_intent_succeeded(payment_intent)
        if not payment_intent.get('metadata', {}).get('plan_id', None):
            return JSONResponse(content={"success": False})
        if not payment_intent.get('metadata', {}).get('company_id', None):
            return JSONResponse(content={"success": False})

        # Create or renew membership
        if payment_intent.get('payment_status', '') == 'paid' and payment_intent.get('mode', '') == 'subscription':

            crud_membership.company_membership.create(
                db,
                company_id=payment_intent.get('metadata', {})['company_id'],
                obj_in=CompanyMembershipCreate(
                    membership_plan_id=payment_intent.get('metadata', {})['plan_id'],
                    auto_renew=True
                )
            )
        else:
            return JSONResponse(content={"success": False})
    else:
        print(f"Unhandled event type {event['type']}")

    return JSONResponse(content={"success": True})


@router.get("/cancel")
async def webhook(request: Request,
                  response: Response,
                  stripe_signature: str = Header(None),
                  db: Session = Depends(get_db), ):
    try:
        payload = await request.body()
    except Exception as e:
        print("⚠️  Error getting request body:", e)
        raise HTTPException(status_code=400, detail="Invalid payload")

    event = None

    try:
        event = json.loads(payload)
    except json.JSONDecodeError as e:
        print("⚠️  Webhook error while parsing basic request:", e)
        return JSONResponse(content={"success": False})

    # Verify Stripe signature if secret is set
    if endpoint_secret:
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=stripe_signature,
                secret=endpoint_secret
            )
        except stripe.error.SignatureVerificationError as e:
            print("⚠️  Webhook signature verification failed:", e)
            return JSONResponse(content={"success": False}, status_code=400)

    if event["type"] in ("subscription.canceled", "subscription.failed"):
        payment_intent = event["data"]["object"]
        print(payment_intent)
        print(f"💰 Payment for {payment_intent['amount']} succeeded.")
        # handle_payment_intent_succeeded(payment_intent)
        if not payment_intent.get('plan_id', None):
            return JSONResponse(content={"success": False})
        if not payment_intent.get('company_id', None):
            return JSONResponse(content={"success": False})
        active = crud_membership.company_membership.get_active_membership(db, company_id=payment_intent['company_id'])
        if active:
            crud_membership.company_membership.cancel(db, id=str(active.id))

    else:
        print(f"Unhandled event type {event['type']}")

    return JSONResponse(content={"success": True})

@router.post("/webhook/subscription", response_model=DataResponse, status_code=status.HTTP_200_OK)
def subscription_webhook(
    payload: dict,
    response: Response,
    db: Session = Depends(get_db),
    x_webhook_token: Optional[str] = Header(default=None, alias="X-Webhook-Token")
) -> DataResponse:
    """
    Webhook endpoint to receive membership subscription results.

    Expected JSON body:
    {
      "event": "subscription.completed" | "subscription.renewed" | "subscription.failed" | "subscription.canceled",
      "company_id": "uuid",
      "membership_plan_id": "uuid",
      "auto_renew": true
    }

    If SETTINGS.MEMBERSHIP_WEBHOOK_SECRET is set, requires X-Webhook-Token header to match.
    """
    # Optional token verification
    if settings and getattr(settings, "MEMBERSHIP_WEBHOOK_SECRET", None):
        secret = settings.MEMBERSHIP_WEBHOOK_SECRET
        if not x_webhook_token or x_webhook_token != secret:
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return DataResponse.error_response(
                message="Invalid webhook token",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

    # Basic validation
    event = payload.get("event")
    company_id = payload.get("company_id")
    membership_plan_id = payload.get("membership_plan_id")
    auto_renew = payload.get("auto_renew", True)

    if not event or not company_id:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DataResponse.error_response(
            message="Missing required fields: event, company_id",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        if event in ("subscription.completed", "subscription.renewed"):
            if not membership_plan_id:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return DataResponse.error_response(
                    message="membership_plan_id is required for completion/renewal events",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            # Create or renew membership
            crud_membership.company_membership.create(
                db,
                company_id=company_id,
                obj_in=CompanyMembershipCreate(
                    membership_plan_id=membership_plan_id,
                    auto_renew=bool(auto_renew)
                )
            )
            return DataResponse.success_response(
                message="Subscription processed successfully",
                status_code=status.HTTP_200_OK
            )
        elif event in ("subscription.canceled", "subscription.failed"):
            # Cancel current active membership if any
            active = crud_membership.company_membership.get_active_membership(db, company_id=company_id)
            if active:
                crud_membership.company_membership.cancel(db, id=str(active.id))
            return DataResponse.success_response(
                message="Subscription cancellation processed",
                status_code=status.HTTP_200_OK
            )
        else:
            # Unknown events are acknowledged to prevent retries, but logged as unsupported
            return DataResponse.success_response(
                message="Event acknowledged (unsupported event type)",
                status_code=status.HTTP_200_OK
            )
    except Exception as e:
        db.rollback()
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return DataResponse.error_response(
            message=f"Failed to process subscription webhook: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
