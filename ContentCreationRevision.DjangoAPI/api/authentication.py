from django.contrib.auth.models import User
from django.conf import settings
from rest_framework import authentication, exceptions
# from msal import ConfidentialClientApplication
import jwt
import requests
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64

class AzureADAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request).split()

        if not auth_header or auth_header[0].lower() != b'bearer':
            raise exceptions.AuthenticationFailed("No token provided")

        token = auth_header[1].decode('utf-8')
        if not token:
            raise exceptions.AuthenticationFailed("No token provided")

        try:
            payload = self.validate_token(token)
            if payload.get("aud") != settings.AZURE_AD["SCOPE"]:
                raise exceptions.AuthenticationFailed("Token is not valid for this scope")
            if payload.get("iss") != f"https://sts.windows.net/{settings.AZURE_AD['TENANT_ID']}/":
                raise exceptions.AuthenticationFailed("Token is not valid for this tenant")

            user_id = payload.get('sub')
            name = payload.get('name')
            # You can create or get the user here if needed
            # user, _ = User.objects.get_or_create(username=user_id, defaults={'first_name': name})
            # return (user, None)
        except Exception as e:
            raise exceptions.AuthenticationFailed(e)

        return None


    def validate_token(self, token):
        TENANT_ID = settings.AZURE_AD["TENANT_ID"]
        API_AUDIENCE = settings.AZURE_AD["SCOPE"]

        jsonurl = requests.get(f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys")
        jwks = jsonurl.json()
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks["keys"]:
             if key["kid"] == unverified_header["kid"]:
                rsa_key = self.construct_rsa_key(key)

        if rsa_key:
            try:
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=["RS256"],
                    audience=API_AUDIENCE,
                    issuer=f"https://sts.windows.net/{TENANT_ID}/"
                )
                return payload
            except jwt.ExpiredSignatureError:
                raise exceptions.AuthenticationFailed("Token expired")
            except jwt.JWTClaimsError:
                raise exceptions.AuthenticationFailed("Invalid claims")
            except Exception as e:
                print("exceptions", e)
                raise exceptions.AuthenticationFailed("Token validation failed")

        raise exceptions.AuthenticationFailed("Unable to find appropriate key")



    def construct_rsa_key(self, key):
        public_key = rsa.RSAPublicNumbers(
            n=int.from_bytes(base64.urlsafe_b64decode(key["n"] + '=='), 'big'),
            e=int.from_bytes(base64.urlsafe_b64decode(key["e"] + '=='), 'big')
        ).public_key(default_backend())

        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem




        # client_app = ConfidentialClientApplication(
        #     settings.AZURE_AD['CLIENT_ID'],
        #     authority=f"{settings.AZURE_AD['AUTHORITY']}/{settings.AZURE_AD['TENANT_ID']}",
        #     client_credential=settings.AZURE_AD['CLIENT_SECRET']
        # )

     
        # decoded_token = client_app.acquire_token_by_refresh_token(token, scopes=[settings.AZURE_AD['SCOPE']])
        # print("ERROR", decoded_token)
        # if 'error' in decoded_token:
        #     raise exceptions.AuthenticationFailed('Token is invalid or expired')

        # # Check for specific scopes in the token's claims
        # if 'scp' in decoded_token and 'User.Read' in decoded_token['scp'].split():
        #     # Continue with authentication
        #     user, _ = User.objects.get_or_create(username=decoded_token['sub'], defaults={'first_name': decoded_token.get('name', '')})
        #     return (user, None)
        # else:
        #     raise exceptions.AuthenticationFailed("Required scope is missing")

        # return None
