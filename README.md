# Artvinci Backend

Django 5 backend application for Artvinci, configured to use MongoDB as the database.

## 📋 Prerequisites

- Python 3.13+
- MongoDB installed and running locally
- MongoDB Compass (optional, for database visualization)

## 🚀 Quick Start

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

Make sure MongoDB is running on your local machine at `localhost:27017`:

```bash
# Check if MongoDB is running
ps aux | grep mongod

# Or start MongoDB if not running
brew services start mongodb-community  # On macOS with Homebrew
# or
sudo systemctl start mongod  # On Linux
```

### 5. Run the Development Server

```bash
python manage.py runserver
```

The server will start at `http://localhost:8000`

**Note:** The database `artvinci_db` will be created automatically when you first write data to it. No migrations are needed at this stage

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

You can verify the connection using the Django shell:

```bash
python manage.py shell
```

Then run:

```python
from django.conf import settings
from pymongo import MongoClient

# Check Django settings
print(f"Database: {settings.DATABASES['default']['NAME']}")
print(f"Host: {settings.DATABASES['default']['CLIENT']['host']}")
print(f"Port: {settings.DATABASES['default']['CLIENT']['port']}")

# Test MongoDB connection
client = MongoClient('localhost', 27017)
print(f"Connected: {client.server_info() is not None}")
print(f"Available databases: {client.list_database_names()}")
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

## 📝 Creating Your First Model

The project is set up with a clean slate. To create your first model:

1. Define your model in `core/models.py`:

```python
from django.db import models

class YourModel(models.Model):
    name = models.CharField(max_length=200)
    # Add your fields here
    
    def __str__(self):
        return self.name
```

2. Create and run migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

3. Your data will be automatically stored in MongoDB collections

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

## 🌐 Building Your API

The project includes Django REST Framework. To create API endpoints:

1. **Create a serializer** in `core/serializers.py`:

```python
from rest_framework import serializers
from .models import YourModel

class YourModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = YourModel
        fields = '__all__'
```

2. **Create views** in `core/views.py`:

```python
from rest_framework import viewsets
from .models import YourModel
from .serializers import YourModelSerializer

class YourModelViewSet(viewsets.ModelViewSet):
    queryset = YourModel.objects.all()
    serializer_class = YourModelSerializer
```

3. **Register URLs** in your urls.py

## 📚 Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Djongo Documentation](https://nesdis.github.io/djongo/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [MongoDB Compass](https://www.mongodb.com/products/compass)

## 📄 License

[Your License Here]

## 👥 Contributors

[Your Name/Team]
