# BookStore Application

A full-stack bookstore application with React frontend and Flask backend, designed for AWS deployment.

## Features

- User authentication (login/register)
- Add new books with title, price, and image
- View all available books
- AWS S3 for image storage
- AWS RDS for database
- AWS EC2 for hosting
- Application Load Balancer for traffic distribution

## Prerequisites

- Node.js and npm
- Python 3.8+
- AWS Account with necessary services configured:
  - S3 Bucket
  - RDS PostgreSQL instance
  - EC2 instance
  - Application Load Balancer
  - VPC

## Backend Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export DATABASE_URL=your_rds_endpoint
export SECRET_KEY=your_secret_key
export AWS_ACCESS_KEY_ID=your_aws_access_key
export AWS_SECRET_ACCESS_KEY=your_aws_secret_key
export S3_BUCKET_NAME=your_bucket_name
```

4. Run the Flask application:
```bash
python backend/app.py
```

## Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm start
```

## AWS Deployment

1. S3 Setup:
   - Create a new S3 bucket
   - Enable public access
   - Configure CORS policy

2. RDS Setup:
   - Create a PostgreSQL instance
   - Note the endpoint, username, and password
   - Configure security groups

3. EC2 Setup:
   - Launch an EC2 instance
   - Install required software (Python, Node.js)
   - Configure security groups
   - Set up environment variables

4. Application Load Balancer:
   - Create a new load balancer
   - Configure target groups
   - Set up listeners

5. VPC Configuration:
   - Create a VPC
   - Set up subnets
   - Configure route tables
   - Set up security groups

## Environment Variables

Create a `.env` file in the backend directory:

```
DATABASE_URL=your_rds_endpoint
SECRET_KEY=your_secret_key
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
S3_BUCKET_NAME=your_bucket_name
```

## Security Considerations

- Use HTTPS for all API calls
- Implement proper CORS policies
- Use environment variables for sensitive data
- Regularly rotate AWS credentials
- Implement proper error handling
- Use secure password hashing
- Implement rate limiting
- Regular security audits

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 