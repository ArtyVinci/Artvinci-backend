# Artvinci Backend

Django 5 backend application for Artvinci, configured to use MongoDB as the database.

## 📋 Prerequisites

- Python 3.13+
- MongoDB installed and running locally
- MongoDB Compass (optional, for database visualization)

## 🚀 Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd artvinci-backend
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify MongoDB is Running

Make sure MongoDB is running on your local machine at `localhost:27017`. You can check this using:

```bash
# Check if MongoDB is running
ps aux | grep mongod

# Or start MongoDB if not running
brew services start mongodb-community  # On macOS with Homebrew
# or
sudo systemctl start mongod  # On Linux
```

### 5. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

This will create the `artvinci_db` database in MongoDB and set up all necessary collections.

### 6. Run the Development Server

```bash
python manage.py runserver
```

The server will start at `http://localhost:8000`

## 🗄️ MongoDB Configuration

### Database Connection

The application connects to MongoDB using the following configuration in `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'djongo',
        'NAME': 'artvinci_db',
        'ENFORCE_SCHEMA': False,
        'CLIENT': {
            'host': 'localhost',
            'port': 27017,
        }
    }
}
```

**Connection URI:** `mongodb://localhost:27017/artvinci_db`

### Viewing Data in MongoDB Compass

1. Open MongoDB Compass
2. Connect to `mongodb://localhost:27017`
3. You should see the `artvinci_db` database listed alongside your other databases (e.g., "courtiq", "samurai-dojo", "steg_interns")
4. Click on `artvinci_db` to explore the collections

## 🧪 Testing the MongoDB Connection

You can test the connection using the Django shell:

```bash
python manage.py shell
```

Then run:

```python
from core.models import Artist

# Create a new artist
artist = Artist(
    name='Pablo Picasso',
    country='Spain',
    art_style='Cubism'
)
artist.save()

# Query all artists
artists = Artist.objects.all()
for artist in artists:
    print(f"{artist.name} - {artist.country} - {artist.art_style}")

# Get count of artists
print(f"Total artists: {Artist.objects.count()}")
```

## 📦 Dependencies

Key packages used for MongoDB integration:

- **djongo (1.3.6)**: Django adapter for MongoDB
- **pymongo (3.12.3)**: Python driver for MongoDB
- **pytz**: Timezone support (required by djongo)

## 🏗️ Project Structure

```
artvinci-backend/
├── artvinci/               # Main project configuration
│   ├── settings.py         # Database and app settings
│   ├── urls.py            # URL routing
│   └── wsgi.py            # WSGI configuration
├── core/                  # Core application
│   ├── models.py          # Database models (Artist, etc.)
│   ├── views.py           # Views/endpoints
│   ├── admin.py           # Admin configuration
│   └── migrations/        # Database migrations
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 📝 Models

### Artist Model

Located in `core/models.py`:

```python
class Artist(models.Model):
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=100)
    art_style = models.CharField(max_length=100)
```

This model is stored in the `artists` collection in MongoDB.

## 🔧 Troubleshooting

### MongoDB Connection Issues

If you encounter connection errors:

1. **Verify MongoDB is running:**
   ```bash
   ps aux | grep mongod
   ```

2. **Check MongoDB logs:**
   ```bash
   tail -f /usr/local/var/log/mongodb/mongo.log  # On macOS
   ```

3. **Test connection with pymongo:**
   ```python
   from pymongo import MongoClient
   client = MongoClient('localhost', 27017)
   print(client.list_database_names())
   ```

### Djongo Warnings

You may see warnings like:
- "This version of djongo does not support 'NULL, NOT NULL column validation check' fully"
- "This version of djongo does not support 'schema validation using CONSTRAINT' fully"

These are expected warnings from djongo and do not affect basic functionality. The migrations and data operations work correctly despite these warnings.

### Missing Dependencies

If you get `ModuleNotFoundError`, ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

## 🌐 API Development

To add REST API endpoints, you can use Django REST Framework (already included):

```python
# In core/serializers.py
from rest_framework import serializers
from .models import Artist

class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = '__all__'
```

```python
# In core/views.py
from rest_framework import viewsets
from .models import Artist
from .serializers import ArtistSerializer

class ArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer
```

## 📚 Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Djongo Documentation](https://nesdis.github.io/djongo/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [MongoDB Compass](https://www.mongodb.com/products/compass)

## 📄 License

[Your License Here]

## 👥 Contributors

[Your Name/Team]
