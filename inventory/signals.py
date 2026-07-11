# signals.py
from django.db.models.signals import pre_delete
from django.dispatch import receiver
import cloudinary.uploader
from .models import Bill  # Yahan apne model ka import check kar lena


@receiver(pre_delete, sender=Bill)
def delete_image_from_cloudinary(sender, instance, **kwargs):
    if instance.bill_image:
        try:
            # CloudinaryField object ke paas .public_id pehle se hoti hai
            public_id = instance.bill_image.public_id
            response = cloudinary.uploader.destroy(public_id)

            if response.get("result") != "ok":
                raise Exception(
                    f"Cloudinary failed with result: {response.get('result')}"
                )

        except Exception as e:
            # Signal ke andar hum direct 'messages' use nahi kar sakte,
            # isliye hum error log kar rahe hain taaki view mein catch kar sakein
            print(f"[CRITICAL ERROR] Cloudinary Deletion Failed: {e}")
