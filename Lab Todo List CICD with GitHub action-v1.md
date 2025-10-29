# Lab 6: CI/CD with GitHub Actions - Todo List Application

## วัตถุประสงค์การทดลอง
1. อธิบายหลักการและกระบวนการ CI/CD (Continuous Integration/Continuous Deployment)
2. สร้าง Flask Application แบบ Production-Ready พร้อม PostgreSQL
3. ใช้ Docker Compose ในการจัดการ Multi-Container Application
4. เขียน Unit Tests และ Integration Tests อย่างมีประสิทธิภาพ
5. สร้าง GitHub Actions Workflow สำหรับ Automated Testing และ Deployment
6. Deploy Application ไปยัง Cloud Platform (Render และ Railway)

## เครื่องมือที่ต้องใช้
- Git และ GitHub Account
- Docker Desktop
- Python 3.11+
- Code Editor (VS Code แนะนำ)
- Render Account (สมัครฟรีที่ render.com)
- Railway Account (สมัครฟรีที่ railway.app)

---

## ส่วนที่ 1: การเตรียมโครงสร้างโปรเจกต์

### ขั้นตอนที่ 1.1: สร้าง GitHub Repository

1. เข้าสู่ GitHub และสร้าง Repository ใหม่
   - คลิก "New repository"
   - ตั้งชื่อ: `flask-todo-cicd`
   - เลือก Public
   - ✅ เลือก "Add a README file"
   - ✅ เลือก "Add .gitignore" → เลือก Python
   - คลิก "Create repository"

2. Clone Repository มายัง Local Machine
```bash
git clone https://github.com/your-username/flask-todo-cicd.git
cd flask-todo-cicd
```

**คำอธิบาย**: การใช้ .gitignore ช่วยป้องกันไม่ให้ไฟล์ที่ไม่จำเป็น (เช่น `__pycache__`, `.env`) ถูก commit ขึ้น repository

### ขั้นตอนที่ 1.2: สร้างโครงสร้างโปรเจกต์

สร้างโครงสร้างโฟลเดอร์ดังนี้:
```bash
mkdir -p app tests .github/workflows
touch app/__init__.py app/models.py app/routes.py app/config.py
touch tests/__init__.py tests/test_app.py
touch requirements.txt Dockerfile docker-compose.yml .env.example
touch .github/workflows/ci-cd.yml
```

**โครงสร้างที่ได้**:
```
flask-todo-cicd/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   └── config.py
├── tests/
│   ├── __init__.py
│   └── test_app.py
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

**คำอธิบาย**: 
- `app/`: เก็บ application code แยกตาม concerns (models, routes, config)
- `tests/`: เก็บ test files แยกจาก application code
- `.github/workflows/`: เก็บ GitHub Actions workflow definitions

---

## ส่วนที่ 2: พัฒนา Flask Todo Application

### ขั้นตอนที่ 2.1: กำหนด Dependencies

สร้างไฟล์ `requirements.txt`:
```txt
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
psycopg2-binary
python-dotenv==1.0.0
gunicorn==21.2.0
pytest==7.4.3
pytest-cov==4.1.0
```

**คำอธิบาย**:
- `Flask`: Web framework หลัก
- `Flask-SQLAlchemy`: ORM สำหรับจัดการฐานข้อมูล
- `psycopg2-binary`: PostgreSQL adapter สำหรับ Python
- `python-dotenv`: โหลด environment variables จาก .env file
- `gunicorn`: WSGI HTTP Server สำหรับ production
- `pytest`, `pytest-cov`: Testing framework และ code coverage

### ขั้นตอนที่ 2.2: สร้าง Configuration

สร้างไฟล์ `app/config.py`:
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@db:5432/todo_dev'
    )

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # Production-specific initialization
        assert os.getenv('DATABASE_URL'), 'DATABASE_URL must be set in production'

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
```

**คำอธิบาย**:
- แยก configuration ตาม environment เพื่อความยืดหยุ่นและความปลอดภัย
- ใช้ environment variables สำหรับข้อมูลที่ sensitive
- Testing ใช้ SQLite in-memory เพื่อความเร็วในการ test

### ขั้นตอนที่ 2.3: สร้าง Database Models

สร้างไฟล์ `app/models.py`:
```python
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Todo(db.Model):
    """Todo item model"""
    __tablename__ = 'todos'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'completed': self.completed,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Todo {self.id}: {self.title}>'
```

**คำอธิบาย**:
- ใช้ SQLAlchemy ORM เพื่อ abstraction layer กับฐานข้อมูล
- `to_dict()` method สำหรับ serialize object เป็น JSON
- `created_at` และ `updated_at` เพื่อ track การเปลี่ยนแปลงข้อมูล

### ขั้นตอนที่ 2.4: สร้าง API Routes

สร้างไฟล์ `app/routes.py`:
```python
from flask import Blueprint, request, jsonify
from app.models import db, Todo
from sqlalchemy.exc import SQLAlchemyError

api = Blueprint('api', __name__)


@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    try:
        db.session.execute(db.text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'database': 'connected'
        }), 200
    except Exception:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': 'Database connection failed'
        }), 503


@api.route('/todos', methods=['GET'])
def get_todos():
    """Get all todo items"""
    try:
        todos = Todo.query.order_by(Todo.created_at.desc()).all()
        return jsonify({
            'success': True,
            'data': [todo.to_dict() for todo in todos],
            'count': len(todos)
        }), 200
    except SQLAlchemyError:
        return jsonify({
            'success': False,
            'error': 'Database error occurred'
        }), 500


@api.route('/todos/<int:todo_id>', methods=['GET'])
def get_todo(todo_id):
    """Get a specific todo item"""
    todo = Todo.query.get(todo_id)
    if not todo:
        return jsonify({
            'success': False,
            'error': 'Todo not found'
        }), 404

    return jsonify({
        'success': True,
        'data': todo.to_dict()
    }), 200


@api.route('/todos', methods=['POST'])
def create_todo():
    """Create a new todo item"""
    data = request.get_json()

    if not data or not data.get('title'):
        return jsonify({
            'success': False,
            'error': 'Title is required'
        }), 400

    try:
        todo = Todo(
            title=data['title'],
            description=data.get('description', '')
        )
        db.session.add(todo)
        db.session.commit()

        return jsonify({
            'success': True,
            'data': todo.to_dict(),
            'message': 'Todo created successfully'
        }), 201
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to create todo'
        }), 500


@api.route('/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    """Update an existing todo item"""
    todo = Todo.query.get(todo_id)
    if not todo:
        return jsonify({
            'success': False,
            'error': 'Todo not found'
        }), 404

    data = request.get_json()

    try:
        if 'title' in data:
            todo.title = data['title']
        if 'description' in data:
            todo.description = data['description']
        if 'completed' in data:
            todo.completed = data['completed']

        db.session.commit()

        return jsonify({
            'success': True,
            'data': todo.to_dict(),
            'message': 'Todo updated successfully'
        }), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to update todo'
        }), 500


@api.route('/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    """Delete a todo item"""
    todo = Todo.query.get(todo_id)
    if not todo:
        return jsonify({
            'success': False,
            'error': 'Todo not found'
        }), 404

    try:
        db.session.delete(todo)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Todo deleted successfully'
        }), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to delete todo'
        }), 500
```

**คำอธิบาย**:
- ใช้ Blueprint เพื่อแยก routes ออกจาก application factory
- `/health` endpoint สำหรับ monitoring และ readiness checks
- แต่ละ endpoint มี error handling และ validation ที่เหมาะสม
- ใช้ HTTP status codes ตาม RESTful conventions

### ขั้นตอนที่ 2.5: สร้าง Application Factory

สร้างไฟล์ `app/__init__.py`:
```python
import os
from flask import Flask, jsonify
from app.models import db
from app.routes import api
from app.config import config

def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(api, url_prefix='/api')
    
    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            'message': 'Flask Todo API',
            'version': '1.0.0',
            'endpoints': {
                'health': '/api/health',
                'todos': '/api/todos'
            }
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Resource not found'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app
```

**คำอธิบาย**:
- ใช้ Application Factory Pattern เพื่อความยืดหยุ่นในการสร้าง app instance
- สามารถสร้าง app ด้วย configuration ต่างๆ ได้ (dev, test, prod)
- Error handlers แบบ centralized

### ขั้นตอนที่ 2.6: สร้าง Entry Point

สร้างไฟล์ `run.py` ในโฟลเดอร์หลัก:
```python
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

---

## ส่วนที่ 3: เขียน Tests

### ขั้นตอนที่ 3.1: สร้าง Test Suite

สร้างไฟล์ `tests/test_app.py`:
```python
import pytest
from app import create_app
from app.models import db, Todo

@pytest.fixture
def app():
    """Create and configure a test app instance"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create a test CLI runner"""
    return app.test_cli_runner()

class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_endpoint(self, client):
        """Test health check returns 200"""
        response = client.get('/api/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'

class TestTodoAPI:
    """Test Todo CRUD operations"""
    
    def test_get_empty_todos(self, client):
        """Test getting todos when database is empty"""
        response = client.get('/api/todos')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['count'] == 0
        assert data['data'] == []
    
    def test_create_todo(self, client):
        """Test creating a new todo"""
        todo_data = {
            'title': 'Test Todo',
            'description': 'This is a test todo'
        }
        response = client.post('/api/todos', json=todo_data)
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['title'] == 'Test Todo'
        assert data['data']['completed'] is False
    
    def test_create_todo_without_title(self, client):
        """Test creating todo without title fails"""
        response = client.post('/api/todos', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data
    
    def test_get_todo_by_id(self, client, app):
        """Test getting a specific todo by ID"""
        # Create a todo first
        with app.app_context():
            todo = Todo(title='Test Todo', description='Test')
            db.session.add(todo)
            db.session.commit()
            todo_id = todo.id
        
        response = client.get(f'/api/todos/{todo_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['title'] == 'Test Todo'
    
    def test_get_nonexistent_todo(self, client):
        """Test getting a todo that doesn't exist"""
        response = client.get('/api/todos/9999')
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
    
    def test_update_todo(self, client, app):
        """Test updating a todo"""
        # Create a todo first
        with app.app_context():
            todo = Todo(title='Original Title')
            db.session.add(todo)
            db.session.commit()
            todo_id = todo.id
        
        update_data = {
            'title': 'Updated Title',
            'completed': True
        }
        response = client.put(f'/api/todos/{todo_id}', json=update_data)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['title'] == 'Updated Title'
        assert data['data']['completed'] is True
    
    def test_delete_todo(self, client, app):
        """Test deleting a todo"""
        # Create a todo first
        with app.app_context():
            todo = Todo(title='To Be Deleted')
            db.session.add(todo)
            db.session.commit()
            todo_id = todo.id
        
        response = client.delete(f'/api/todos/{todo_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        
        # Verify it's deleted
        response = client.get(f'/api/todos/{todo_id}')
        assert response.status_code == 404
    
    def test_get_all_todos(self, client, app):
        """Test getting all todos"""
        # Create multiple todos
        with app.app_context():
            todos = [
                Todo(title='Todo 1'),
                Todo(title='Todo 2'),
                Todo(title='Todo 3')
            ]
            db.session.add_all(todos)
            db.session.commit()
        
        response = client.get('/api/todos')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['count'] == 3
```

**คำอธิบาย**:
- ใช้ pytest fixtures เพื่อ setup และ teardown test environment
- แยก test classes ตาม functionality
- ครอบคลุม happy path และ edge cases
- Test ใช้ SQLite in-memory เพื่อความเร็ว

### ขั้นตอนที่ 3.2: สร้าง pytest Configuration

สร้างไฟล์ `pytest.ini` ในโฟลเดอร์หลัก:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --cov=app
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
```

**คำอธิบาย**:
- กำหนด test discovery patterns
- เปิดใช้ code coverage reporting ในหลายรูปแบบ
- `-v` สำหรับ verbose output

---

## ส่วนที่ 4: Docker Configuration

### ขั้นตอนที่ 4.1: สร้าง Dockerfile

สร้างไฟล์ `Dockerfile`:
```dockerfile
# Build stage
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/health')" || exit 1

# Run application with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "run:app"]
```

**คำอธิบาย**:
- **Multi-stage build**: แยก build dependencies ออกจาก runtime image เพื่อลดขนาด
- **Non-root user**: เพิ่มความปลอดภัยโดยไม่รัน container ด้วย root
- **Health check**: ตรวจสอบสถานะ application อัตโนมัติ
- **Gunicorn**: WSGI server สำหรับ production (ไม่ใช้ Flask development server)

### ขั้นตอนที่ 4.2: สร้าง Docker Compose

สร้างไฟล์ `docker-compose.yml`:
```yaml
services:
  db:
    image: postgres:16-alpine
    container_name: todo_postgres
    environment:
      POSTGRES_DB: todo_dev
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app_network

  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: todo_app
    environment:
      FLASK_ENV: development
      DATABASE_URL: postgresql://postgres:postgres@db:5432/todo_dev
      SECRET_KEY: dev-secret-key-12345
    ports:
      - "5000:5000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - .:/app
    networks:
      - app_network
    command: flask run --host=0.0.0.0

volumes:
  postgres_data:

networks:
  app_network:
    driver: bridge
```

**คำอธิบาย**:
- **Services isolation**: แยก database และ application เป็น containers ต่างหาก
- **Health checks**: รอให้ database พร้อมก่อนเริ่ม application
- **Volumes**: เก็บข้อมูล database แบบ persistent
- **Networks**: สร้าง isolated network สำหรับ inter-container communication
- **Development mode**: ใช้ Flask development server และ mount source code เพื่อ hot reload

### ขั้นตอนที่ 4.3: สร้าง Environment File Template

สร้างไฟล์ `.env.example`:
```env
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=change-this-in-production

# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@db:5432/todo_dev

# Production Settings (for deployment)
# DATABASE_URL=your-production-database-url
# SECRET_KEY=your-production-secret-key
```

**คำอธิบาย**: 
- Template สำหรับ environment variables
- ไม่ควร commit `.env` file จริงลง git (ถูกระบุใน .gitignore แล้ว)

---

## ส่วนที่ 5: ทดสอบ Application ในเครื่อง

### ขั้นตอนที่ 5.1: Build และ Run ด้วย Docker Compose

```bash
# Build images
docker compose build

# Start services
# สำหรับ Mac OS หากต้องการใช้ port 5000 ให้ปิด Airplay Receiver (System Settings-> General -> Airdrop & Handoff -> AirPlay Receiver )
docker compose up -d

# ตรวจสอบ logs
docker compose logs -f app

# ตรวจสอบว่า services ทำงาน
docker compose ps
```

**คำอธิบาย**:
- `-d` flag สำหรับ run ใน background (detached mode)
- `logs -f` แสดง logs แบบ real-time

### ขั้นตอนที่ 5.2: ทดสอบ API Endpoints

ใช้ curl หรือ Postman ทดสอบ:

```bash
# Health check
curl http://localhost:5000/api/health

# Get all todos
curl http://localhost:5000/api/todos

# Create a todo
curl -X POST http://localhost:5000/api/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Learn Docker", "description": "Master containerization"}'

# Get specific todo (replace 1 with actual ID)
curl http://localhost:5000/api/todos/1

# Update todo
curl -X PUT http://localhost:5000/api/todos/1 \
  -H "Content-Type: application/json" \
  -d '{"completed": true}'

# Delete todo
curl -X DELETE http://localhost:5000/api/todos/1
```

### ขั้นตอนที่ 5.3: รัน Tests

```bash
# รัน tests ใน Docker container
docker compose exec app pytest

# หรือรันในเครื่องโดยตรง (ต้องติดตั้ง dependencies ก่อน)
python -m venv venv  # python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pytest
```

**ผลลัพธ์ที่คาดหวัง**:
- Tests ทั้งหมดผ่าน (สีเขียว)
- Code coverage อย่างน้อย 90%
  
## *** ผลการทดสอบระบบมี % ยังไม่สูง ต้องแก้ไขให้ทดสอบครอบคลุมอย่างน้อย 90% แก้ไขดังนี้***

## 1: เพิ่ม Test Cases ใน tests/test_app.py
 ### 1.1 เพิ่ม class TestAppFactory (ใหม่ทั้งหมด)"""
```python
class TestAppFactory:
    """Test application factory and configuration"""
    
    def test_app_creation(self, app):
        """Test app is created successfully"""
        assert app is not None
        assert app.config['TESTING'] is True
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info"""
        response = client.get('/')
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'version' in data
        assert 'endpoints' in data
    
    def test_404_error_handler(self, client):
        """Test 404 error handler"""
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data
    def test_exception_handler(self, app):
        """Test generic exception handler"""
        # 1. ปิด TESTING mode ชั่วคราว
        app.config['TESTING'] = False
        
        @app.route('/test-error')
        def trigger_error():
            raise Exception('Test error')
        
        # 2. ทดสอบ
        with app.test_client() as test_client:
            response = test_client.get('/test-error')
            assert response.status_code == 500
            assert 'Internal server error' in response.get_json()['error']
        
        # 3. เปิด TESTING mode กลับ
        app.config['TESTING'] = True
```
### 1.2 แก้ไข class TestHealthCheck จากเดิม 1 test: เพิ่มเป็น 2 test 
```python
    def test_health_endpoint_success(self, client):
        """Test health check returns 200 when database is healthy"""
        response = client.get('/api/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['database'] == 'connected'
    
    @patch('app.routes.db.session.execute')
    def test_health_endpoint_database_error(self, mock_execute, client):
        """Test health check returns 503 when database is down"""
        mock_execute.side_effect = Exception('Database connection failed')
        
        response = client.get('/api/health')
        assert response.status_code == 503
        data = response.get_json()
        assert data['status'] == 'unhealthy'
        assert data['database'] == 'disconnected'
        assert 'error' in data
```
### 1.3 เพิ่ม class TestTodoModel 
```python
class TestTodoModel:
    """Test Todo model methods"""
    
    def test_todo_to_dict(self, app):
        """Test todo model to_dict method"""
        with app.app_context():
            todo = Todo(title='Test Todo', description='Test Description')
            db.session.add(todo)
            db.session.commit()
            
            todo_dict = todo.to_dict()
            assert todo_dict['title'] == 'Test Todo'
            assert todo_dict['description'] == 'Test Description'
            assert todo_dict['completed'] is False
            assert 'id' in todo_dict
            assert 'created_at' in todo_dict
            assert 'updated_at' in todo_dict
    
    def test_todo_repr(self, app):
        """Test todo model __repr__ method"""
        with app.app_context():
            todo = Todo(title='Test Todo')
            db.session.add(todo)
            db.session.commit()
            
            repr_str = repr(todo)
            assert 'Todo' in repr_str
            assert 'Test Todo' in repr_str
```
### 1.4 แก้ไข class TestTodoAPI จากเดิม 
```python
    """Test Todo CRUD operations"""
    
    def test_get_empty_todos(self, client):
        """Test getting todos when database is empty"""
        response = client.get('/api/todos')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['count'] == 0
        assert data['data'] == []
    
    def test_create_todo_with_full_data(self, client):
        """Test creating a new todo with title and description"""
        todo_data = {
            'title': 'Test Todo',
            'description': 'This is a test todo'
        }
        response = client.post('/api/todos', json=todo_data)
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['title'] == 'Test Todo'
        assert data['data']['description'] == 'This is a test todo'
        assert data['data']['completed'] is False
        assert 'message' in data
    
    def test_create_todo_with_title_only(self, client):
        """Test creating todo with only title (description is optional)"""
        todo_data = {'title': 'Test Todo Only Title'}
        response = client.post('/api/todos', json=todo_data)
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['title'] == 'Test Todo Only Title'
        assert data['data']['description'] == ''
    
    def test_create_todo_without_title(self, client):
        """Test creating todo without title fails validation"""
        response = client.post('/api/todos', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data
        assert 'Title is required' in data['error']
    
    def test_create_todo_with_none_data(self, client):
        """Test creating todo with None data"""
        response = client.post('/api/todos', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
    
    @patch('app.routes.db.session.commit')
    def test_create_todo_database_error(self, mock_commit, client):
        """Test database error during todo creation"""
        mock_commit.side_effect = SQLAlchemyError('Database error')
        
        response = client.post('/api/todos', json={'title': 'Test'})
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data
    
    def test_get_todo_by_id(self, client, app):
        """Test getting a specific todo by ID"""
        with app.app_context():
            todo = Todo(title='Test Todo', description='Test Description')
            db.session.add(todo)
            db.session.commit()
            todo_id = todo.id
        
        response = client.get(f'/api/todos/{todo_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['title'] == 'Test Todo'
        assert data['data']['description'] == 'Test Description'
    
    def test_get_nonexistent_todo(self, client):
        """Test getting a todo that doesn't exist"""
        response = client.get('/api/todos/9999')
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data
        assert 'not found' in data['error'].lower()
    
    def test_update_todo_title(self, client, app):
        """Test updating todo title"""
        with app.app_context():
            todo = Todo(title='Original Title')
            db.session.add(todo)
            db.session.commit()
            todo_id = todo.id
        
        update_data = {'title': 'Updated Title'}
        response = client.put(f'/api/todos/{todo_id}', json=update_data)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['title'] == 'Updated Title'
        assert 'message' in data
    
    def test_update_todo_description(self, client, app):
        """Test updating todo description"""
        with app.app_context():
            todo = Todo(title='Test', description='Old Description')
            db.session.add(todo)
            db.session.commit()
            todo_id = todo.id
        
        update_data = {'description': 'New Description'}
        response = client.put(f'/api/todos/{todo_id}', json=update_data)
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['description'] == 'New Description'
    
    def test_update_todo_completed_status(self, client, app):
        """Test updating todo completed status"""
        with app.app_context():
            todo = Todo(title='Test')
            db.session.add(todo)
            db.session.commit()
            todo_id = todo.id
        
        update_data = {'completed': True}
        response = client.put(f'/api/todos/{todo_id}', json=update_data)
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['completed'] is True
    
    def test_update_todo_all_fields(self, client, app):
        """Test updating all todo fields at once"""
        with app.app_context():
            todo = Todo(title='Original', description='Old')
            db.session.add(todo)
            db.session.commit()
            todo_id = todo.id
        
        update_data = {
            'title': 'New Title',
            'description': 'New Description',
            'completed': True
        }
        response = client.put(f'/api/todos/{todo_id}', json=update_data)
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['title'] == 'New Title'
        assert data['data']['description'] == 'New Description'
        assert data['data']['completed'] is True
    
    def test_update_nonexistent_todo(self, client):
        """Test updating a todo that doesn't exist"""
        response = client.put('/api/todos/9999', json={'title': 'Updated'})
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
    
    @patch('app.routes.db.session.commit')
    def test_update_todo_database_error(self, mock_commit, client, app):
        """Test database error during todo update"""
        # สร้าง todo ก่อน (ไม่ถูก mock)
        with app.app_context():
            todo = Todo(title='Test')
            db.session.add(todo)
            db.session.commit()
            todo_id = todo.id

        # แล้วค่อย mock เฉพาะตอน update
        with patch('app.routes.db.session.commit') as mock_commit:
            mock_commit.side_effect = SQLAlchemyError('Database error')
            response = client.put(f'/api/todos/{todo_id}', json={'title': 'New'})

    def test_delete_todo(self, client, app):
        """Test deleting a todo"""
        with app.app_context():
            todo = Todo(title='To Be Deleted')
            db.session.add(todo)
            db.session.commit()
            todo_id = todo.id
        
        response = client.delete(f'/api/todos/{todo_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'message' in data
        
        # Verify it's deleted
        response = client.get(f'/api/todos/{todo_id}')
        assert response.status_code == 404
    
    def test_delete_nonexistent_todo(self, client):
        """Test deleting a todo that doesn't exist"""
        response = client.delete('/api/todos/9999')
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
    
    @patch('app.routes.db.session.delete')
    def test_delete_todo_database_error(self, mock_commit, client, app):
        """Test database error during todo deletion"""
        with app.app_context():
            todo = Todo(title='Test')
            db.session.add(todo)
            db.session.commit()
            todo_id = todo.id
        
        mock_commit.side_effect = SQLAlchemyError('Database error')
        
        response = client.delete(f'/api/todos/{todo_id}')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
    
    def test_get_all_todos_ordered(self, client, app):
        """Test getting all todos returns them in correct order"""
        with app.app_context():
            todos = [
                Todo(title='Todo 1'),
                Todo(title='Todo 2'),
                Todo(title='Todo 3')
            ]
            db.session.add_all(todos)
            db.session.commit()
        
        response = client.get('/api/todos')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['count'] == 3
        # Should be ordered by created_at desc (newest first)
        assert data['data'][0]['title'] == 'Todo 3'
        assert data['data'][2]['title'] == 'Todo 1'
    
    @patch('app.routes.Todo.query')
    def test_get_todos_database_error(self, mock_query, client):
        """Test database error when getting todos"""
        mock_query.order_by.return_value.all.side_effect = SQLAlchemyError('DB Error')
        
        response = client.get('/api/todos')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
```
### 1.5 เพิ่ม TestIntegration 
```python
class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_complete_todo_lifecycle(self, client):
        """Test complete CRUD workflow"""
        # Create
        create_response = client.post('/api/todos', json={
            'title': 'Integration Test Todo',
            'description': 'Testing full lifecycle'
        })
        assert create_response.status_code == 201
        todo_id = create_response.get_json()['data']['id']
        
        # Read
        read_response = client.get(f'/api/todos/{todo_id}')
        assert read_response.status_code == 200
        assert read_response.get_json()['data']['title'] == 'Integration Test Todo'
        
        # Update
        update_response = client.put(f'/api/todos/{todo_id}', json={
            'title': 'Updated Integration Test',
            'completed': True
        })
        assert update_response.status_code == 200
        updated_data = update_response.get_json()['data']
        assert updated_data['title'] == 'Updated Integration Test'
        assert updated_data['completed'] is True
        
        # Delete
        delete_response = client.delete(f'/api/todos/{todo_id}')
        assert delete_response.status_code == 200
        
        # Verify deletion
        verify_response = client.get(f'/api/todos/{todo_id}')
        assert verify_response.status_code == 404
    
    def test_multiple_todos_workflow(self, client):
        """Test working with multiple todos"""
        # Create multiple todos
        for i in range(5):
            response = client.post('/api/todos', json={
                'title': f'Todo {i+1}',
                'completed': i % 2 == 0  # Alternate completed status
            })
            assert response.status_code == 201
        
        # Get all and verify count
        response = client.get('/api/todos')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 5
        
        # Update some
        todo_id = data['data'][0]['id']
        response = client.put(f'/api/todos/{todo_id}', json={'completed': True})
        assert response.status_code == 200
        
        # Delete some
        response = client.delete(f'/api/todos/{todo_id}')
        assert response.status_code == 200
        
        # Verify count decreased
        response = client.get('/api/todos')
        assert response.get_json()['count'] == 4
```
### 1.5 เพิ่มการ import
```python
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
```
## 2. เพิ่มไฟล์ tests/test_config.py (ใหม่ทั้งไฟล์)
    - เดิม: ไม่มีการ test configuration เลย
    - ใหม่: สร้างไฟล์ใหม่พร้อม 4 test classes
```python 
import pytest
import os
from app.config import Config, DevelopmentConfig, TestingConfig, ProductionConfig, config

class TestConfig:
    """Test base configuration"""
    
    def test_base_config_has_secret_key(self):
        """Test base config has secret key"""
        assert hasattr(Config, 'SECRET_KEY')
        assert Config.SECRET_KEY is not None
    
    def test_sqlalchemy_track_modifications_disabled(self):
        """Test SQLAlchemy track modifications is disabled"""
        assert Config.SQLALCHEMY_TRACK_MODIFICATIONS is False

class TestDevelopmentConfig:
    """Test development configuration"""
    
    def test_debug_enabled(self):
        """Test debug mode is enabled in development"""
        assert DevelopmentConfig.DEBUG is True
    
    def test_has_database_uri(self):
        """Test development config has database URI"""
        assert hasattr(DevelopmentConfig, 'SQLALCHEMY_DATABASE_URI')
        assert DevelopmentConfig.SQLALCHEMY_DATABASE_URI is not None

class TestTestingConfig:
    """Test testing configuration"""
    
    def test_testing_enabled(self):
        """Test testing flag is enabled"""
        assert TestingConfig.TESTING is True
    
    def test_uses_sqlite_memory(self):
        """Test testing uses SQLite in-memory database"""
        assert 'sqlite:///:memory:' in TestingConfig.SQLALCHEMY_DATABASE_URI
    
    def test_csrf_disabled(self):
        """Test CSRF is disabled for testing"""
        assert TestingConfig.WTF_CSRF_ENABLED is False

class TestProductionConfig:
    """Test production configuration"""
    
    def test_debug_disabled(self):
        """Test debug mode is disabled in production"""
        assert ProductionConfig.DEBUG is False
    
    def test_requires_database_url(self, monkeypatch):
        """Test production requires DATABASE_URL environment variable"""
        # Remove DATABASE_URL if it exists
        monkeypatch.delenv('DATABASE_URL', raising=False)
        
        from app import create_app
        with pytest.raises(AssertionError):
            app = create_app('production')

class TestConfigSelector:
    """Test configuration selector"""
    
    def test_config_contains_all_environments(self):
        """Test config dict has all environment configurations"""
        assert 'development' in config
        assert 'testing' in config
        assert 'production' in config
        assert 'default' in config
    
    def test_default_is_development(self):
        """Test default configuration is development"""
        assert config['default'] == DevelopmentConfig
```
## 3. อัพเดท pytest.ini 
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --cov=app
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=90         
filterwarnings =
    ignore::DeprecationWarning  
```
## 4. อัพเดท requirements.txt 
```plaintext
pytest-mock==3.12.0              # ← เพิ่ม: บรรทัดนี้ สำหรับ mocking  database errors
```
## 5. เพ่ิ่มใน app/__init__.py
```python
@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all unhandled exceptions"""
    db.session.rollback()
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500
```


## 6. รัน Tests และตรวจสอบ Coverage 
```bash
pytest --cov=app --cov-report=term-missing --cov-report=html

# ดู detailed HTML report 
open htmlcov/index.html  # macOS
# หรือ 
xdg-open htmlcov/index.html  # Linux
#  หรือ 
start htmlcov/index.html  # Windows
```

## แนบรูปผลการทดลองการทดสอบระบบ

# แนบรูปผลการทดลองที่นี่
![alt text](image.png)

## คำถามการทดลอง
ให้จับคู่ Code ส่วนของการทดสอบ กับ Code การทำงาน มาอย่างน้อย 3 ฟังก์ชัน พร้อมอธิบายการทำงานของแต่ละกรณี

# ตอบคำถามที่นี่
คู่ที่ 1 : ฟังก์ชัน /api/health
อธิบาย
กรณีปกติ (Healthy):
เมื่อระบบฐานข้อมูลตอบกลับปกติ (SELECT 1 สำเร็จ) ส่งค่า HTTP 200 และสถานะ healthy
test จะตรวจสอบให้แน่ใจว่าข้อมูลถูกต้อง
กรณีผิดพลาด (Unhealthy):
เมื่อ mock ทำให้ query ล้มเหลว ฟังก์ชันจับ error แล้วส่ง HTTP 503
 test ตรวจสอบว่า message เป็น unhealthy และมี error แสดงออกมา

คู่ที่ 2 : ฟังก์ชัน POST /api/todos (เพิ่มงานใหม่)
อธิบาย
กรณีปกติ (สร้างสำเร็จ)  POST ข้อมูลครบ title + description
เพิ่มในฐานข้อมูลและคืน HTTP 201 พร้อมข้อมูล todo ที่สร้าง
กรณีไม่กรอก title  ระบบตรวจสอบ input แล้ว return 400 + ข้อความ “Title is required”
กรณีฐานข้อมูลล้มเหลว  mock commit ให้ error  ตรวจสอบว่า route ส่งสถานะ 500 และ rollback

คู่ที่ 3 : ฟังก์ชัน GET /api/todos/<id> (ดูรายละเอียดงาน)
อธิบาย
กรณีพบ Todo  ดึงข้อมูลจากฐานข้อมูล  คืนค่า 200 + ข้อมูล Todo
test ตรวจสอบ title, description ว่าตรงกัน
กรณีไม่พบ Todo  คืนค่า 404 พร้อมข้อความ “Todo not found”
test ตรวจสอบว่าคำว่า “not found” อยู่ใน error message จริง




### ขั้นตอนที่ 5.4: Cleanup  (ไม่ต้องทดลอง สามารถข้ามได้)

```bash
# Stop services
docker compose down

# Stop and remove volumes
docker compose down -v
```

---

## ส่วนที่ 6: GitHub Actions CI/CD Pipeline

### ขั้นตอนที่ 6.1: สร้าง Workflow File

สร้างไฟล์ `.github/workflows/ci-cd.yml`:
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  PYTHON_VERSION: '3.11'
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # Job 1: Run Tests
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run linting
        run: |
          pip install flake8
          flake8 app --count --select=E9,F63,F7,F82 --show-source --statistics
          flake8 app --count --max-line-length=120 --statistics
      
      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
          FLASK_ENV: testing
        run: |
          pytest --cov=app --cov-report=xml --cov-report=term
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: false

  # Job 2: Build Docker Image
  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: test
    if: github.event_name == 'push'
    
    permissions:
      contents: read
      packages: write
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # Job 3: Deploy to Render
  deploy-render:
    name: Deploy to Render
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    
    steps:
      - name: Trigger Render Deployment
        run: |
          curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK_URL }}
      
      - name: Wait for deployment
        run: sleep 60
      
      - name: Health check
        run: |
          for i in {1..5}; do
            if curl -f ${{ secrets.RENDER_APP_URL }}/api/health; then
              echo "Deployment successful!"
              exit 0
            fi
            echo "Attempt $i failed, retrying..."
            sleep 10
          done
          echo "Deployment health check failed"
          exit 1

  # Job 4: Deploy to Railway
  deploy-railway:
    name: Deploy to Railway
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Install Railway CLI
        run: npm install -g @railway/cli
      
      - name: Deploy to Railway
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: |
          railway link ${{ secrets.RAILWAY_PROJECT_ID }}
          railway up --detach
      
      - name: Wait for deployment
        run: sleep 60
      
      - name: Health check
        run: |
          for i in {1..5}; do
            if curl -f ${{ secrets.RAILWAY_APP_URL }}/api/health; then
              echo "Railway deployment successful!"
              exit 0
            fi
            echo "Attempt $i failed, retrying..."
            sleep 10
          done
          echo "Railway deployment health check failed"
          exit 1
```

**คำอธิบาย Workflow**:

1. **Test Job**:
   - รัน automated tests ทุกครั้งที่มี push หรือ PR
   - ใช้ PostgreSQL service container
   - ทำ linting ด้วย flake8
   - วัด code coverage และส่งไปยัง Codecov

2. **Build Job**:
   - Build Docker image และ push ไปยัง GitHub Container Registry
   - รันเฉพาะเมื่อมี push (ไม่รันใน PR)
   - ใช้ Docker layer caching เพื่อความเร็ว

3. **Deploy Jobs**:
   - Deploy ไปทั้ง Render และ Railway
   - รันเฉพาะใน main branch
   - มี health check หลัง deployment

---


## ส่วนที่ 7: Setup Deployment Platforms และ GitHub Secrets

### ขั้นตอนที่ 7.1: Deploy to Render

#### **7.1.1 สร้าง PostgreSQL Database บน Render**

1. ไปที่ [render.com](https://render.com) และ login/signup
2. คลิก **"New +"** → เลือก **"PostgreSQL"**
3. ตั้งค่าดังนี้:
   - **Name**: `todo-db`
   - **Database**: `todo_db`
   - **User**: `todo_user`
   - **Region**: เลือก `Singapore` (ใกล้ที่สุด) หรือ `Oregon`
   - **PostgreSQL Version**: `16`
   - **Plan**: **Free**
4. คลิก **"Create Database"**
5. รอประมาณ 1-2 นาทีจนสถานะเป็น "Available"
6. ในหน้า Database Info:
   - หา **"Internal Database URL"** (รูปแบบ: `postgresql://...`)
   - **คัดลอก URL นี้ไว้ใช้ในขั้นตอนถัดไป**

**หมายเหตุ**: Internal Database URL จะมีรูปแบบประมาณนี้:
```
postgresql://todo_user:xxxxx@dpg-xxxxx-a/todo_db_xx
```

---

#### **7.1.2 สร้าง Web Service บน Render**

1. กลับไปที่ Dashboard หรือ My Workspace แล้วคลิก **"New +"** → **"Web Service"**
2. คลิก **"Connect a repository"**
   - เลือก **"Configure account"** แล้วให้สิทธิ์ Render เข้าถึง GitHub
   - เลือก Only select repositories แล้วเลือก repository `flask-todo-cicd` แล้วกดปุ่ม Install
   - เลือกรูปแบบ Confirm access โดยใช้ passkey หรือรูปแบบอื่น
   - เลือก GitHub Repository 
3. ตั้งค่า Web Service:
   - **Name**: `flask-todo-app` (ชื่อนี้จะเป็นส่วนหนึ่งของ URL)
   - **Region**: เลือกเช่นเดียวกับ Database (Singapore)
   - **Branch**: `main`
   - **Root Directory**: ว่างไว้
4. ตั้งค่า Web Service:
   - **Name**: `flask-todo-app` (ชื่อนี้จะเป็นส่วนหนึ่งของ URL)
   - **Region**: เลือกเดียวกับ Database → `Singapore` หรือ `Oregon`
   - **Branch**: `main`
   - **Root Directory**: ปล่อยว่างไว้ (ใช้ root ของ repo)
   - **Plan**: **Free**
   - **Start Command กำหนดเป็น**: After CI Check pass
```bash
   gunicorn --bind 0.0.0.0:$PORT --workers 4 --timeout 120 run:app"
```
5. ตั้งค่า **Environment Variables**: 
   
   
   | Key | Value |
   |-----|-------|
   | `FLASK_ENV` | `production` |
   | `DATABASE_URL` | *[วาง Internal Database URL จากขั้นตอน 7.1.1]* |
   | `SECRET_KEY` | *[สร้าง random string โดยกดปุ่ม Generate]* |
   | `PORT` | `5000` |

   **วิธีสร้าง SECRET_KEY เองด้วย python command**:
   ```bash
   # ใน Terminal/Command Prompt
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   
6. คลิก **"Deploy Web Service"**

3. Render จะเริ่ม build จาก Dockerfile:
   - แสดง build logs ในหน้า deploy
   - ใช้เวลาประมาณ 3-5 นาที (ครั้งแรกอาจนานกว่า)
   - เมื่อสำเร็จจะเห็นสถานะเป็น **"Live"** สีเขียว

**คำอธิบาย**:
- Render จะ detect Dockerfile อัตโนมัติและใช้มันใน build process
- ไม่ต้องเลือก runtime manually เหมือนแพลตฟอร์มอื่น
- ถ้า Dockerfile ไม่ถูก detect ให้ตรวจสอบว่าไฟล์อยู่ที่ root ของ repository
- Environment variable `PORT` สำคัญ - Render จะ inject port number ที่ต้องการ

**หมายเหตุสำคัญ**:
- ❗ Render Free tier มีข้อจำกัด: service จะ sleep หลังไม่มีการใช้งาน 15 นาที
- 🔄 Request แรกหลัง sleep จะใช้เวลา 30-60 วินาทีในการ wake up
- 💡 สำหรับ production จริงควรใช้ paid plan เพื่อให้ service ทำงานตลอดเวลา

---

#### **7.1.3 หา Render Secrets สำหรับ GitHub Actions**

**🔑 Secret 1: RENDER_DEPLOY_HOOK_URL**

1. ในหน้า Web Service ไปที่แท็บ **"Settings"**
2. Scroll ลงไปหาส่วน **"Deploy Hook"**
3. คัดลอก URL ที่แสดง (รูปแบบ: `https://api.render.com/deploy/srv-...`)
4. **เก็บ URL นี้ไว้** → นี่คือ `RENDER_DEPLOY_HOOK_URL`

**📝 ตัวอย่าง**:
```
https://api.render.com/deploy/srv-abcd1234efgh5678?key=xyz789abc
```

**🔑 Secret 2: RENDER_APP_URL**

1. ที่หน้า Overview ของ Web Service
2. จะเห็น URL ที่ Render สร้างให้ (รูปแบบ: `https://your-app-name.onrender.com`)
3. **คัดลอก URL นี้** → นี่คือ `RENDER_APP_URL`

**📝 ตัวอย่าง**:
```
https://flask-todo-app.onrender.com
```

**หมายเหตุ**: 
- ชื่อ app ใน URL จะตรงกับที่ตั้งไว้ในขั้นตอนที่ 7.1.2
- ถ้าชื่อซ้ำกัน Render จะเพิ่มตัวเลขต่อท้าย เช่น `flask-todo-app-1`

**เพิ่ม RENDER_DEPLOY_HOOK_URL และ RENDER_APP_URL บน GitHub Repository**
**ทำการ push ไปที่ GitHub Repository** แล้วตรวจสอบผลการทำงาน
## บันทึกรูปผลการทำงาน
```bash
# บันทึกรูปผลการทำงานที่นี่
``` 

---



### ขั้นตอนที่ 7.2: Deploy to Railway

#### **7.2.1 สร้างโปรเจกต์บน Railway**

1. ไปที่ [railway.app](https://railway.app)
2. คลิก **"Login"** → เลือก **"Login with GitHub"**
3. ให้สิทธิ์ Railway เข้าถึง GitHub
4. คลิก **"New Project"**
5. เลือก **"Deploy from GitHub repo"**
6. เลือก repository `flask-todo-cicd`
7. คลิก **"Deploy Now"**
8. Railway จะ detect Dockerfile อัตโนมัติและเริ่ม deploy

---

#### **7.2.2 เพิ่ม PostgreSQL Database**

1. ในโปรเจกต์เดียวกัน คลิก **"+ New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway จะสร้าง database และตั้ง environment variables อัตโนมัติ
3. รอประมาณ 30 วินาทีจน database พร้อม

---

#### **7.2.3 ตั้งค่า Environment Variables**

1. คลิกที่ **Flask service** (ไม่ใช่ database)
2. ไปที่แท็บ **"Variables"**
3. เพิ่ม variables ดังนี้:

   | Variable | Value | คำอธิบาย |
   |----------|-------|----------|
   | `FLASK_ENV` | `production` | ตั้งเป็น production mode |
   | `SECRET_KEY` | *[สร้าง random string]* | ใช้คำสั่ง Python ข้างบน |
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | อ้างอิงจาก database ที่สร้าง |

   **การใช้ Reference Variables**:
   - พิมพ์ `${{` แล้ว Railway จะแสดง autocomplete
   - เลือก `Postgres.DATABASE_URL` (Postgres คือชื่อ service ของ database)
   
4. คลิก **"Deploy"** หรือรอ auto-deploy

---

#### **7.2.4 Enable Public Domain**

1. ในหน้า Flask service ไปที่แท็บ **"Settings"**
2. หาส่วน **"Networking"** → **"Public Networking"**
3. คลิก **"Generate Domain"**
4. Railway จะสร้าง URL ให้ (รูปแบบ: `https://your-project.up.railway.app`)
5. **คัดลอก URL นี้** → นี่คือ `RAILWAY_APP_URL`

**📝 ตัวอย่าง**:
```
https://flask-todo-cicd-production.up.railway.app
```

---

#### **7.2.5 หา Railway Secrets สำหรับ GitHub Actions**

**🔑 Secret 1: RAILWAY_TOKEN**

1. คลิกที่โปรไฟล์ของคุณ (มุมบนขวา) → เลือก **"Account Settings"**
2. ในเมนูด้านซ้าย เลือก **"Tokens"**
3. คลิก **"Create Token"** หรือ **"New Token"**
4. ตั้งชื่อ Token: `GitHub Actions` (อะไรก็ได้)
5. คัดลอก Token ที่ได้ → **เก็บไว้ทันที (จะไม่แสดงอีก)** → นี่คือ `RAILWAY_TOKEN`

**📝 ตัวอย่าง**:
```
railway_abc123def456ghi789jkl012mno345pqr678stu901
```

**🔑 Secret 2: RAILWAY_PROJECT_ID**

1. กลับไปที่ Project ของคุณใน Railway
2. ไปที่ **"Settings"** ของโปรเจกต์ (ไอคอน gear ⚙️)
3. หาส่วน **"General"** → **"Project ID"**
4. คัดลอก Project ID → นี่คือ `RAILWAY_PROJECT_ID`

**📝 ตัวอย่าง**:
```
a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8
```

**หมายเหตุ**: Project ID จะเป็น UUID รูปแบบ

---

### ขั้นตอนที่ 7.3: เพิ่ม Secrets ใน GitHub Repository

ตอนนี้เรามี **5 secrets** แล้ว มาเพิ่มใน GitHub กัน:

1. ไปที่ GitHub repository ของคุณ (`flask-todo-cicd`)
2. คลิก **"Settings"** (แท็บบนสุด)
3. ในเมนูด้านซ้าย เลือก **"Secrets and variables"** → **"Actions"**
4. คลิก **"New repository secret"**
5. เพิ่ม secrets ทั้ง 5 ตัวดังนี้:

| Name | Value | ได้มาจาก |
|------|-------|---------|
| `RENDER_DEPLOY_HOOK_URL` | `https://api.render.com/deploy/srv-...` | Render Settings → Deploy Hook |
| `RENDER_APP_URL` | `https://flask-todo-app.onrender.com` | Render Overview → URL |
| `RAILWAY_TOKEN` | `railway_abc123...` | Railway Account Settings → Tokens |
| `RAILWAY_PROJECT_ID` | `a1b2c3d4-e5f6-...` | Railway Project Settings → Project ID |
| `RAILWAY_APP_URL` | `https://...up.railway.app` | Railway Settings → Networking |

**วิธีเพิ่มแต่ละ secret**:
1. คลิก **"New repository secret"**
2. ใส่ **Name** (ต้องตรงกับตารางข้างบน)
3. ใส่ **Value** (paste ค่าที่คัดลอกไว้)
4. คลิก **"Add secret"**
5. ทำซ้ำจนครบ 5 secrets

---

### ขั้นตอนที่ 7.4: ตรวจสอบว่า Secrets ครบถ้วน

หลังจากเพิ่ม secrets แล้ว ควรเห็น:

```
✅ RAILWAY_APP_URL
✅ RAILWAY_PROJECT_ID
✅ RAILWAY_TOKEN
✅ RENDER_APP_URL
✅ RENDER_DEPLOY_HOOK_URL
```

**หมายเหตุสำคัญ**:
- ❌ **ห้ามใส่เครื่องหมาย `/` ท้าย URL** เช่น `https://app.com/` (ผิด)
- ✅ ต้องเป็น `https://app.com` (ถูก)
- 🔒 Secrets จะไม่แสดงค่าอีกหลังจาก save (ถูกซ่อนไว้)
- 🔄 ถ้าจำ secret ไม่ได้ ให้ลบแล้วสร้างใหม่

---

### ขั้นตอนที่ 7.5: ทดสอบ Secrets

**ทดสอบว่า Render ทำงาน**:
```bash
# ทดสอบ Deploy Hook (จะ trigger deployment)
curl -X POST "YOUR_RENDER_DEPLOY_HOOK_URL"

# ทดสอบ App URL
curl https://YOUR_RENDER_APP_URL/api/health
```

**ทดสอบว่า Railway ทำงาน**:
```bash
# ทดสอบ App URL
curl https://YOUR_RAILWAY_APP_URL/api/health
```

---

### 📋 Checklist: ตรวจสอบก่อน Push Code

ก่อน push code และ trigger GitHub Actions ให้ตรวจสอบ:

- [ ] Render Database สร้างเสร็จและสถานะ "Available"
- [ ] Render Web Service deploy สำเร็จและสถานะ "Live"
- [ ] Railway Database และ Web Service ทำงานปกติ
- [ ] สร้าง GitHub Secrets ครบ 5 ตัว
- [ ] ทดสอบ health endpoints ของทั้ง Render และ Railway ได้
- [ ] URL ไม่มี `/` ท้าย
- [ ] DATABASE_URL ใช้ Internal URL (สำหรับ Render)

---

### 🔍 การ Debug ถ้ามีปัญหา

**ปัญหา: Render ไม่เจอ Dockerfile**
- ตรวจสอบว่าไฟล์ `Dockerfile` อยู่ที่ root ของ repository
- ตรวจสอบว่าชื่อไฟล์เป็น `Dockerfile` (ไม่มี extension, D ตัวใหญ่)
- ลอง push commit ใหม่แล้ว redeploy

**ปัญหา: Render build ล้มเหลว**
- ดู build logs ใน Render Dashboard → Deploy → Logs
- ตรวจสอบว่า Dockerfile syntax ถูกต้อง
- ทดสอบ build ในเครื่องก่อน: `docker build -t test .`

**ปัญหา: Render deployment ล้มเหลว**
- ตรวจสอบ Logs ใน Render Dashboard
- ตรวจสอบว่า DATABASE_URL ถูกต้อง
- ตรวจสอบว่า PORT environment variable ถูกตั้งค่า
- ตรวจสอบว่า Dockerfile expose port 5000

**ปัญหา: Railway deployment ล้มเหลว**
- ตรวจสอบว่า RAILWAY_TOKEN ยังใช้ได้ (ไม่หมดอายุ)
- ตรวจสอบว่า PROJECT_ID ถูกต้อง
- ดู deployment logs ใน Railway Dashboard

**ปัญหา: GitHub Actions ไม่ทำงาน**
- ตรวจสอบชื่อ secrets ตรงกับใน workflow file หรือไม่
- ดู logs ใน GitHub Actions tab
- ตรวจสอบว่า branch เป็น `main` หรือไม่

**ปัญหา: Health check ล้มเหลว**
- ตรวจสอบว่า `/api/health` endpoint ทำงาน
- ลองเรียก URL ด้วย browser หรือ curl
- ตรวจสอบว่า application เริ่มต้นสำเร็จ (ดู logs)

**ปัญหา: Database connection error**
- ตรวจสอบว่า DATABASE_URL format ถูกต้อง
- ใช้ Internal Database URL สำหรับ Render (เร็วกว่าและฟรี)
- ตรวจสอบว่า database service ทำงานอยู่

---

## ส่วนที่ 8: ทดสอบ CI/CD Pipeline

### ขั้นตอนที่ 8.1: Commit และ Push Code

```bash
# เพิ่มไฟล์ทั้งหมด
git add .

# Commit
git commit -m "feat: implement todo API with CI/CD pipeline"

# Push to GitHub
git push origin main
```

**คำอธิบาย**: การ push จะ trigger GitHub Actions workflow อัตโนมัติ

### ขั้นตอนที่ 8.2: ตรวจสอบ Workflow

1. ไปที่ GitHub repository → Actions tab
2. คลิกที่ workflow run ล่าสุด
3. ตรวจสอบแต่ละ job:
   - ✅ Test job ต้องผ่านทั้งหมด
   - ✅ Build job ต้อง build image สำเร็จ
   - ✅ Deploy jobs ต้อง deploy สำเร็จ

**การ Debug ถ้ามีปัญหา**:
- คลิกที่ job ที่ failed
- อ่าน error logs
- แก้ไขปัญหาแล้ว push ใหม่

### ขั้นตอนที่ 8.3: ทดสอบ Deployed Application

**ทดสอบ Render**:
```bash
# Health check
curl https://your-app.onrender.com/api/health

# Create todo
curl -X POST https://your-app.onrender.com/api/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Test from Render", "description": "Testing deployment"}'

# Get todos
curl https://your-app.onrender.com/api/todos
```

**ทดสอบ Railway**:
```bash
# Health check
curl https://your-app.up.railway.app/api/health

# Create todo
curl -X POST https://your-app.up.railway.app/api/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Test from Railway", "description": "Testing deployment"}'

# Get todos
curl https://your-app.up.railway.app/api/todos
```

---

## ส่วนที่ 9: Best Practices และการปรับปรุง

### 9.1 Security Best Practices

**เพิ่มการรักษาความปลอดภัย**:

1. **Rate Limiting** - ป้องกัน abuse:
```bash
pip install Flask-Limiter
```

เพิ่มใน `app/__init__.py`:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
```

2. **CORS Configuration** - ควบคุม access:
```bash
pip install Flask-CORS
```

3. **Input Validation** - ใช้ marshmallow หรือ pydantic

4. **Secrets Management**:
   - ไม่เก็บ secrets ใน code
   - ใช้ environment variables
   - ใช้ secrets management service (AWS Secrets Manager, HashiCorp Vault)

### 9.2 Monitoring และ Logging

**เพิ่ม Structured Logging**:

สร้างไฟล์ `app/logging_config.py`:
```python
import logging
import sys

def setup_logging(app):
    """Configure application logging"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    
    return app.logger
```


### 9.3 Database Migrations

**ใช้ Flask-Migrate สำหรับจัดการ database schema**:

```bash
pip install Flask-Migrate
```

สร้างไฟล์ `migrations/__init__.py` และเพิ่มใน application:
```python
from flask_migrate import Migrate

migrate = Migrate(app, db)
```

### 9.4 Documentation

**เพิ่ม API Documentation ด้วย Swagger**:
```bash
pip install flask-swagger-ui
```

**สร้าง README.md ที่ดี**:
```markdown
# Flask Todo API

## Features
- RESTful API
- PostgreSQL database
- Docker containerization
- CI/CD with GitHub Actions
- Automated testing

## Quick Start
\`\`\`bash
docker-compose up -d
\`\`\`

## API Endpoints
- `GET /api/health` - Health check
- `GET /api/todos` - Get all todos
- `POST /api/todos` - Create todo
- ...
```

---

## ส่วนที่ 10: การทดสอบและประเมินผล

### 10.1 Checklist การทดลอง

ตรวจสอบว่าทำสำเร็จทุกข้อ:

- [ ] สร้าง GitHub repository และ clone ลงเครื่อง
- [ ] สร้าง Flask application ที่มี CRUD operations ครบถ้วน
- [ ] เขียน tests ที่ครอบคลุม code coverage > 80%
- [ ] สร้าง Dockerfile ที่ optimize แล้ว
- [ ] สร้าง docker-compose.yml ที่แยก services
- [ ] รัน application ด้วย Docker และทดสอบใน local สำเร็จ
- [ ] สร้าง GitHub Actions workflow ที่มีทั้ง CI และ CD
- [ ] Deploy ไปยัง Render สำเร็จ
- [ ] Deploy ไปยัง Railway สำเร็จ
- [ ] ทดสอบ API endpoints บน production
- [ ] Health checks ทำงานถูกต้อง
- [ ] Auto-deployment ทำงานเมื่อ push code ใหม่

### 10.2 คำถามทบทวน


1. **Docker Architecture**:
   - เหตุใดจึงต้องแยก database และ application เป็นคนละ containers ?
   - Multi-stage build มีประโยชน์อย่างไร?

2. **Testing Strategy**:
   - การวัด code coverage มีความสำคัญอย่างไร?

3. **Deployment**:
   - Health check endpoint มีความสำคัญอย่างไร?
   - Render และ Railway มีความแตกต่างกันอย่่างไร?


---

**แหล่งข้อมูลเพิ่มเติม**:
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [12-Factor App Methodology](https://12factor.net/)

