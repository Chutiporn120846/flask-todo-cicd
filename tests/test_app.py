import pytest
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
from app.models import db, Todo


# ------------------------
# Test App Factory
# ------------------------
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
        app.config['TESTING'] = False

        @app.route('/test-error')
        def trigger_error():
            raise Exception('Test error')

        with app.test_client() as test_client:
            response = test_client.get('/test-error')
            assert response.status_code == 500
            assert 'Internal server error' in response.get_json()['error']

        app.config['TESTING'] = True

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


# ------------------------
# Test Todo Model
# ------------------------
class TestTodoModel:
    """Test Todo model methods"""
    
    def test_todo_to_dict(self, app):
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
        with app.app_context():
            todo = Todo(title='Test Todo')
            db.session.add(todo)
            db.session.commit()
            repr_str = repr(todo)
            assert 'Todo' in repr_str
            assert 'Test Todo' in repr_str


# ------------------------
# Test Todo API CRUD
# ------------------------
class TestTodoAPI:
    """Test Todo CRUD operations"""
    
    def test_get_empty_todos(self, client):
        response = client.get('/api/todos')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 0

    def test_create_todo_with_full_data(self, client):
        response = client.post('/api/todos', json={'title': 'Test Todo', 'description': 'A'})
        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['title'] == 'Test Todo'

    def test_create_todo_without_title(self, client):
        response = client.post('/api/todos', json={})
        assert response.status_code == 400
        assert 'error' in response.get_json()

    @patch('app.routes.db.session.commit')
    def test_create_todo_database_error(self, mock_commit, client):
        mock_commit.side_effect = SQLAlchemyError('DB error')
        response = client.post('/api/todos', json={'title': 'Test'})
        assert response.status_code == 500


# ------------------------
# Integration tests
# ------------------------
class TestIntegration:
    """Integration tests for complete workflows"""

    def test_complete_todo_lifecycle(self, client):
        # Create
        create = client.post('/api/todos', json={'title': 'Integration Test'})
        assert create.status_code == 201
        todo_id = create.get_json()['data']['id']

        # Read
        read = client.get(f'/api/todos/{todo_id}')
        assert read.status_code == 200

        # Update
        update = client.put(f'/api/todos/{todo_id}', json={'completed': True})
        assert update.status_code == 200
        assert update.get_json()['data']['completed'] is True

        # Delete
        delete = client.delete(f'/api/todos/{todo_id}')
        assert delete.status_code == 200

        # Verify deleted
        verify = client.get(f'/api/todos/{todo_id}')
        assert verify.status_code == 404
