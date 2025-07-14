
from app import app

# Vercel expects this function
def handler(request):
    return app(request.environ, lambda *args: None)

# Also keep the original for local development
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 
