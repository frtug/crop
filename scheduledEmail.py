import smtplib
import ssl
from email.message import EmailMessage
from dotenv import load_dotenv
import os

load_dotenv()
# Define email sender and receiver

def schedule_send_email(cropInfo,email_receiver,date):
    email_sender = os.getenv('SENDER_EMAIL')
    email_password = os.getenv('GOOGLE_PASS')
    # email_receiver = 'write-email-receiver-here'

    # Set the subject and body of the email
    subject = 'Scheduled email for Crop fertilizer'
    crop = cropInfo['crop']
    environment =cropInfo['environment']
    maturity =cropInfo['maturity']
    fertilizer =cropInfo['fertilizerApplicationSchedule']
    description =cropInfo['description']
    suitableRegions = cropInfo['suitableRegions']

    message = f"""
    Name: {crop} \n
    Environment: {environment} \n
    SuitableRegions : {suitableRegions} \n
    Maturity: {maturity} \n
    Fertilizer:{fertilizer} \n
    Description:{description} \n
    Created On :{date} \n
    """
    body = message
    em = EmailMessage()
    em['From'] = email_sender
    em['To'] = email_receiver
    em['Subject'] = subject
    em.set_content(body)

    # Add SSL (layer of security)
    context = ssl.create_default_context()

    # Log in and send the email
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(email_sender, email_password)
        smtp.sendmail(email_sender, email_receiver, em.as_string())


# import datetime
# from googleapiclient.discovery import build
# from google.oauth2 import service_account
# import base64
# # Set up credentials and authenticate with Gmail API


# # Function to create a MIME message for the email
# def create_message(sender, to, subject,message_text):
#     message = {}  # Initialize the message dictionary
    
#     # Assign the encoded message to the 'raw' key
#     message['raw'] = base64.urlsafe_b64encode(message_text.encode('utf-8')).decode('utf-8')
    
#     return message

# # Function to schedule sending the email
# def schedule_send_email(service, message, send_d,recipient_email):
#     sender = 'theinnovatronindustries@gmail.com'
#     recipient = recipient_email
#     subject = 'Scheduled Email'

#     # Set the desired send date and time (10 days from now in this example)

#     # Create the email message
#     msg = create_message(sender, recipient, subject, message)
#     send_date = datetime.datetime.now() + datetime.timedelta(days=10)
#     send_time = send_date.isoformat() + 'Z'  # Format the send date in ISO 8601 format

#     # Set the 'sendAt' parameter to schedule the email for the specified time
#     msg['sendAt'] = send_time

#     # Send the email using the Gmail API
#     request = service.users().messages().send(userId='me', body=msg).execute()
#     print('Email scheduled for:', send_time)

# # Example usage


# # Schedule sending the email
