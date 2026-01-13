
from mailersend import MailerSendClient, EmailBuilder, EmailContact

client = MailerSendClient("mlsn.0df98a7c40217fe6591b656a5a92e6c07efb90ead52d257fe79b4c2b51f9fd2c")

# Build email using EmailBuilder
email = (EmailBuilder()
     .from_email("info@salona.me", "Salona")
     .to_many([{"email": 'emirze2013@gmail.com', "name": "Recipient"}])
     .subject('test')
     .html('')
     .text('that is test')
     .build())

# Send email using MailerSend API
response = client.emails.send(email)