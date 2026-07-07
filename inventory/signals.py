# import os
# import base64
# import re
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import Bill
# from groq import Groq
# from django.conf import settings


# @receiver(post_save, sender=Bill)
# def extract_bill_amount(sender, instance, created, **kwargs):
#     # 1. Sirf tabhi run ho agar bill naya create hua ho aur image मौजूद (exist) ho
#     if created and instance.bill_image:
#         # Absolute path verify karo
#         file_path = os.path.join(settings.MEDIA_ROOT, str(instance.bill_image))

#         if not os.path.exists(file_path):
#             print(f"DEBUG: File not found at {file_path}")
#             return

#         try:
#             # 2. Groq Client initialize karo
#             client = Groq(api_key=os.getenv("GROQ_API_KEY"))

#             # 3. Image ko Base64 mein convert karo
#             with open(file_path, "rb") as image_file:
#                 encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

#             # 4. Groq API Request (Vision Model)
#             # Yahan wo model naam daalo jo aapke dashboard mein active hai
#             response = client.chat.completions.create(
#                 model="llama-3.2-90b-vision-instruct",
#                 messages=[
#                     {
#                         "role": "user",
#                         "content": [
#                             {
#                                 "type": "text",
#                                 "text": "Extract the total numeric amount from this bill. Only return the number.",
#                             },
#                             {
#                                 "type": "image_url",
#                                 "image_url": {
#                                     "url": f"data:image/jpeg;base64,{encoded_string}"
#                                 },
#                             },
#                         ],
#                     }
#                 ],
#             )

#             # 5. Result process karo
#             extracted_text = response.choices[0].message.content.strip()

#             # Sirf digits aur decimal point nikalo
#             cleaned_amount = re.search(r"\d+(\.\d{1,2})?", extracted_text)

#             if cleaned_amount:
#                 instance.total_amount = float(cleaned_amount.group())
#                 instance.save(update_fields=["total_amount"])
#                 print(
#                     f"SUCCESS: Extracted amount {instance.total_amount} for Bill #{instance.id}"
#                 )

#         except Exception as e:
#             print(f"CRITICAL ERROR in Signals: {e}")
