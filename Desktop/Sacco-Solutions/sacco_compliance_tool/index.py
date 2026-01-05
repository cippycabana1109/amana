from app import app

# Vercel serverless function entry point
def handler(request):
    """Vercel serverless function handler."""
    return app(request.environ, lambda status, headers: None)

# Alternative approach for Vercel
def lambda_handler(event, context):
    """AWS Lambda style handler for Vercel compatibility."""
    return app(event, context)
