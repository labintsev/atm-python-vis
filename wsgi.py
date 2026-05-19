from app import app, init_db

# Initialize database on startup
if init_db():
    print("Database initialized for production")
else:
    print("Warning: Database connection failed")

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=5005, threads=4)
