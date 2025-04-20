# AWS Deployment Guide for Bookstore Application

This guide walks through the process of deploying the Bookstore application on AWS using EC2, RDS, S3, and other services.

## 1. Prerequisites

- AWS account with administrator access
- AWS CLI installed and configured
- Git repository with your application code
- Domain name (optional, but recommended for production)

## 2. Architecture Overview

```
┌─────────────┐     ┌────────────┐     ┌──────────────┐     ┌─────────┐
│ Application │     │   Amazon   │     │    Amazon    │     │ Amazon  │
│ Load        │────▶│    EC2     │────▶│     RDS      │     │   S3    │
│ Balancer    │     │ (Backend)  │     │ (PostgreSQL) │     │(Images) │
└─────────────┘     └────────────┘     └──────────────┘     └─────────┘
       ▲                  ▲
       │                  │
       │                  │
┌─────────────┐     ┌────────────┐
│    User     │     │   Amazon   │
│   Browser   │────▶│    EC2     │
│             │     │(Frontend)  │
└─────────────┘     └────────────┘
```

## 3. Setting up VPC and Networking

### Create a VPC

1. Go to the VPC Dashboard in the AWS Console
2. Click "Create VPC"
3. Enter the following details:
   - Name: `bookstore-vpc`
   - IPv4 CIDR block: `10.0.0.0/16`
   - Click "Create VPC"

### Create Subnets

Create at least 4 subnets (2 public, 2 private) across different Availability Zones:

1. Go to Subnets in the VPC Dashboard
2. Click "Create subnet"
3. Create the following subnets:
   - `public-subnet-1` in AZ1, CIDR: `10.0.1.0/24`
   - `public-subnet-2` in AZ2, CIDR: `10.0.2.0/24`
   - `private-subnet-1` in AZ1, CIDR: `10.0.3.0/24`
   - `private-subnet-2` in AZ2, CIDR: `10.0.4.0/24`

### Create Internet Gateway

1. Go to Internet Gateways in the VPC Dashboard
2. Click "Create internet gateway"
3. Name it `bookstore-igw` and click "Create"
4. Select the new IGW and click "Attach to VPC"
5. Select your `bookstore-vpc` and click "Attach"

### Create Route Tables

1. Go to Route Tables in the VPC Dashboard
2. Create a public route table:
   - Name: `bookstore-public-rt`
   - VPC: `bookstore-vpc`
   - Add a route: `0.0.0.0/0` -> `bookstore-igw`
   - Associate with `public-subnet-1` and `public-subnet-2`

3. Create a private route table:
   - Name: `bookstore-private-rt`
   - VPC: `bookstore-vpc`
   - Associate with `private-subnet-1` and `private-subnet-2`

## 4. Setting up RDS (PostgreSQL)

1. Go to the RDS Dashboard
2. Click "Create database"
3. Choose "Standard create"
4. Select PostgreSQL
5. Choose "Free tier" for development or "Production" for production
6. Settings:
   - DB instance identifier: `bookstore-db`
   - Master username: `bookstore_user`
   - Master password: (Create a strong password)
7. Instance configuration:
   - Use DB instance class appropriate for your needs (e.g., `db.t3.micro` for dev)
8. Storage:
   - Allocated storage: 20 GB (adjust as needed)
   - Enable storage autoscaling
9. Connectivity:
   - VPC: `bookstore-vpc`
   - Subnet group: Create new DB Subnet group with `private-subnet-1` and `private-subnet-2`
   - Public access: No
   - VPC security group: Create new, name it `bookstore-db-sg`
10. Database authentication: Password authentication
11. Additional configuration:
    - Initial database name: `bookstore`
    - Backup retention period: 7 days
12. Click "Create database"

## 5. Setting up S3 for Image Storage

1. Go to the S3 dashboard
2. Click "Create bucket"
3. Bucket name: `bookstore-images-<unique-id>` (must be globally unique)
4. Region: Choose the same region as your other resources
5. Block all public access: Uncheck if you want public access to images
6. Bucket versioning: Disabled (or Enable if you need version control for images)
7. Click "Create bucket"

### Configure CORS for S3 Bucket

1. Go to your bucket and select the "Permissions" tab
2. Scroll down to "Cross-origin resource sharing (CORS)"
3. Click "Edit" and add this configuration:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
    "AllowedOrigins": ["*"],  // In production, restrict to your domain
    "ExposeHeaders": []
  }
]
```

## 6. Setting up EC2 for Backend

1. Go to the EC2 dashboard
2. Click "Launch instance"
3. Name: `bookstore-backend`
4. Application and OS: Amazon Linux 2023
5. Instance type: t2.micro (or appropriate for your needs)
6. Key pair: Create or select existing
7. Network settings:
   - VPC: `bookstore-vpc`
   - Subnet: `public-subnet-1`
   - Auto-assign public IP: Enable
   - Security group: Create new security group
     - Name: `bookstore-backend-sg`
     - Allow SSH (port 22) from your IP
     - Allow HTTP (port 80) from anywhere
     - Allow HTTPS (port 443) from anywhere
     - Allow port 5000 from ALB security group (once created)
8. Configure storage: 8 GB (default, adjust as needed)
9. Advanced details:
   - User data:

```bash
#!/bin/bash
yum update -y
yum install -y python3 python3-pip git
pip3 install --upgrade pip
```

10. Click "Launch instance"

### Install and Configure Backend

SSH into your instance and follow these steps:

```bash
# Clone your repository
git clone <your-repo-url>
cd bookstore/backend

# Install dependencies
pip3 install -r requirements.txt

# Create environment file
cat > .env << EOF
DATABASE_URL=postgresql://bookstore_user:<password>@<rds-endpoint>:5432/bookstore
SECRET_KEY=<your-secret-key>
JWT_SECRET_KEY=<your-jwt-secret-key>
AWS_ACCESS_KEY_ID=<your-aws-access-key>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-key>
S3_BUCKET_NAME=bookstore-images-<unique-id>
EOF

# Install and configure Gunicorn
pip3 install gunicorn

# Create a systemd service file
sudo tee /etc/systemd/system/bookstore.service > /dev/null << EOF
[Unit]
Description=Bookstore Backend
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/bookstore/backend
ExecStart=/usr/local/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl enable bookstore
sudo systemctl start bookstore
```

## 7. Setting up EC2 for Frontend

1. Go to the EC2 dashboard
2. Click "Launch instance"
3. Name: `bookstore-frontend`
4. Application and OS: Amazon Linux 2023
5. Instance type: t2.micro (or appropriate for your needs)
6. Key pair: Create or select existing
7. Network settings:
   - VPC: `bookstore-vpc`
   - Subnet: `public-subnet-1`
   - Auto-assign public IP: Enable
   - Security group: Create new security group
     - Name: `bookstore-frontend-sg`
     - Allow SSH (port 22) from your IP
     - Allow HTTP (port 80) from anywhere
     - Allow HTTPS (port 443) from anywhere
8. Configure storage: 8 GB (default, adjust as needed)
9. Advanced details:
   - User data:

```bash
#!/bin/bash
yum update -y
yum install -y nodejs npm git
```

10. Click "Launch instance"

### Install and Configure Frontend

SSH into your instance and follow these steps:

```bash
# Clone your repository
git clone <your-repo-url>
cd bookstore/frontend

# Edit the .env file to point to your backend
cat > .env << EOF
REACT_APP_API_URL=http://<backend-instance-public-dns>:5000
EOF

# Install dependencies
npm install

# Build the application
npm run build

# Install and configure Nginx
sudo yum install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx

# Configure Nginx to serve the React app
sudo tee /etc/nginx/conf.d/bookstore.conf > /dev/null << EOF
server {
    listen 80;
    server_name _;
    
    location / {
        root /home/ec2-user/bookstore/frontend/build;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }
}
EOF

# Remove default config and restart Nginx
sudo rm /etc/nginx/nginx.conf.default
sudo systemctl restart nginx
```

## 8. Setting up Application Load Balancer

1. Go to the EC2 dashboard > Load Balancers
2. Click "Create Load Balancer"
3. Choose "Application Load Balancer"
4. Basic configuration:
   - Name: `bookstore-alb`
   - Scheme: Internet-facing
   - IP address type: IPv4
5. Network mapping:
   - VPC: `bookstore-vpc`
   - Mappings: Select both `public-subnet-1` and `public-subnet-2`
6. Security groups:
   - Create a new security group:
     - Name: `bookstore-alb-sg`
     - Allow HTTP (port 80) from anywhere
     - Allow HTTPS (port 443) from anywhere
7. Listeners and routing:
   - Create target groups:
     - Backend target group:
       - Name: `bookstore-backend-tg`
       - Protocol: HTTP, Port: 5000
       - Target type: Instances
       - VPC: `bookstore-vpc`
       - Protocol version: HTTP1
       - Health check path: `/books`
       - Register targets: Add your backend instance
     - Frontend target group:
       - Name: `bookstore-frontend-tg`
       - Protocol: HTTP, Port: 80
       - Target type: Instances
       - VPC: `bookstore-vpc`
       - Protocol version: HTTP1
       - Health check path: `/`
       - Register targets: Add your frontend instance
8. Configure listeners:
   - HTTP:80: Forward to `bookstore-frontend-tg`
   - Create a new listener:
     - Protocol: HTTP, Port: 5000
     - Forward to: `bookstore-backend-tg`
9. Click "Create load balancer"

## 9. Setting up IAM Permissions

Create IAM policy and role for your EC2 instance to access S3:

1. Go to IAM dashboard
2. Create a policy:
   - Name: `BookstoreS3Access`
   - Service: S3
   - Actions: 
     - ListBucket
     - GetObject
     - PutObject
     - DeleteObject
   - Resources: 
     - Bucket: `arn:aws:s3:::bookstore-images-<unique-id>`
     - Object: `arn:aws:s3:::bookstore-images-<unique-id>/*`
3. Create a role:
   - Name: `BookstoreEC2Role`
   - Trusted entity: EC2
   - Attach the `BookstoreS3Access` policy
4. Attach the role to your EC2 instance:
   - Go to EC2 dashboard
   - Select your backend instance
   - Actions > Security > Modify IAM role
   - Select `BookstoreEC2Role`
   - Save

## 10. Setting up Domain and SSL (Optional)

1. Register a domain in Route 53 or use an existing domain
2. Request an SSL certificate in AWS Certificate Manager
3. Create a record in Route 53 to point to your ALB
4. Update your ALB listeners to use HTTPS with your certificate

## 11. Updating Configuration

### Update Backend Environment Variables

```bash
DATABASE_URL=postgresql://bookstore_user:<password>@<rds-endpoint>:5432/bookstore
SECRET_KEY=<your-secret-key>
JWT_SECRET_KEY=<your-jwt-secret-key>
AWS_ACCESS_KEY_ID=<your-aws-access-key>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-key>
S3_BUCKET_NAME=bookstore-images-<unique-id>
```

### Update Frontend Environment

```
REACT_APP_API_URL=https://<your-domain-or-alb-dns>/api
```

## 12. Security Considerations

1. Enable AWS WAF on your ALB
2. Enable encryption at rest for RDS
3. Set up proper backup for RDS
4. Implement CloudWatch monitoring and alarms
5. Set up proper VPC Flow Logs
6. Consider AWS Shield for DDoS protection
7. Use AWS Secrets Manager for sensitive information

## 13. Scaling Considerations

1. Set up Auto Scaling Groups for EC2 instances
2. Consider using ElastiCache for session management
3. Implement CloudFront for content delivery

## 14. Monitoring and Maintenance

1. Set up CloudWatch dashboards
2. Create alarms for key metrics
3. Implement log aggregation with CloudWatch Logs
4. Create a maintenance plan for OS and package updates

## 15. Cost Optimization

1. Consider reserving instances for long-term use
2. Set up budget alerts
3. Use AWS Cost Explorer to identify optimization opportunities
4. Implement lifecycle policies for S3 objects

---

This deployment architecture provides a solid foundation for your bookstore application, with proper separation of concerns, security, and scalability. For a production environment, you might want to add more advanced features like CI/CD pipelines, automated testing, and disaster recovery planning. 