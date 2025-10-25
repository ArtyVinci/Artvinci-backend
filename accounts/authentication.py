"""
Custom JWT Authentication for MongoEngine
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from .models import User


class MongoEngineJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that works with MongoEngine User model.
    
    Override get_user() to fetch user from MongoDB instead of SQL database.
    """
    
    def get_user(self, validated_token):
        """
        Retrieve user from MongoDB using the user_id in the JWT token.
        
        Args:
            validated_token: The validated JWT token
            
        Returns:
            User: MongoEngine User document
            
        Raises:
            InvalidToken: If user not found or invalid token
        """
        try:
            # Get user_id from token payload
            user_id = validated_token.get('user_id')
            
            if not user_id:
                raise InvalidToken('Token contained no recognizable user identification')
            
            # Fetch user from MongoDB using MongoEngine
            user = User.objects(id=user_id).first()
            
            if not user:
                raise AuthenticationFailed('User not found', code='user_not_found')
            
            # Check if user is verified
            if not user.is_verified:
                raise AuthenticationFailed('User account is not verified', code='not_verified')
            
            return user
            
        except User.DoesNotExist:
            raise InvalidToken('User not found')
        except Exception as e:
            raise InvalidToken(f'Token is invalid or expired: {str(e)}')
