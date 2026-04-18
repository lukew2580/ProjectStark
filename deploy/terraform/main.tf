# Hardwareless AI — Terraform Infrastructure
# Infrastructure as Code for AWS (EKS + RDS + ElastiCache + S3)
# Usage:
#   terraform init
#   terraform plan -var='domain=hardwareless.ai'
#   terraform apply

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# Variables
variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "domain" {
  description = "Root domain for TLS certificates"
  type        = string
  default     = "hardwareless.ai"
}

variable "env" {
  description = "Environment name (dev/staging/prod)"
  type        = string
  default     = "production"
}

variable "node_count" {
  description = "Number of Kubernetes nodes"
  type        = number
  default     = 3
}

variable "instance_type" {
  description = "EC2 instance type for worker nodes"
  type        = string
  default     = "t3.large"
}

# ——————————————————————————————
# VPC & Networking
# ——————————————————————————————
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = {
    Name = "${var.env}-hdc-vpc"
  }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
  tags = { Name = "${var.env}-hdc-igw" }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  map_public_ip_on_launch = true
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  tags = { Name = "${var.env}-hdc-public-${count.index}" }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags = { Name = "${var.env}-hdc-private-${count.index}" }
}

resource "aws_eip" "nat" {
  count  = 2
  domain = "vpc"
}

resource "aws_nat_gateway" "gw" {
  count         = 2
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  depends_on    = [aws_internet_gateway.gw]
  tags = { Name = "${var.env}-hdc-nat-${count.index}" }
}

resource "aws_route_table" "private" {
  count  = 2
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.gw[count.index].id
  }
  tags = { Name = "${var.env}-hdc-private-rt-${count.index}" }
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

data "aws_availability_zones" "available" {}

# ——————————————————————————————
# EKS Cluster
# ——————————————————————————————
resource "aws_eks_cluster" "hdc" {
  name     = "${var.env}-hdc-cluster"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.28"
  
  vpc_config {
    subnet_ids = aws_subnet.private[*].id
  }
  
  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_service_policy,
  ]
}

resource "aws_eks_node_group" "workers" {
  cluster_name    = aws_eks_cluster.hdc.name
  node_group_name = "${var.env}-hdc-nodes"
  node_role_arn   = aws_iam_role.eks_node.arn
  subnet_ids      = aws_subnet.private[*].id
  
  scaling_config {
    desired_size = var.node_count
    max_size     = 10
    min_size     = 2
  }
  
  instance_types = [var.instance_type]
  
  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
  ]
}

# IAM roles for EKS
resource "aws_iam_role" "eks_cluster" {
  name = "${var.env}-hdc-eks-cluster-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.eks_cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_iam_role_policy_attachment" "eks_service_policy" {
  role       = aws_iam_role.eks_cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSServicePolicy"
}

resource "aws_iam_role" "eks_node" {
  name = "${var.env}-hdc-eks-node-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  role       = aws_iam_role.eks_node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  role       = aws_iam_role.eks_node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "eks_container_registry_policy" {
  role       = aws_iam_role.eks_node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# ——————————————————————————————
# Data Stores (Redis, PostgreSQL)
# ——————————————————————————————
resource "aws_elasticache_subnet_group" "hdc" {
  name       = "${var.env}-hdc-cache-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_security_group" "redis" {
  name        = "${var.env}-hdc-redis-sg"
  description = "Allow Redis traffic"
  vpc_id      = aws_vpc.main.id
  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    security_groups = [aws_security_group.eks.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_elasticache_cluster" "hdc" {
  cluster_id           = "${var.env}-hdc-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.hdc.name
  security_group_ids   = [aws_security_group.redis.id]
}

resource "aws_security_group" "eks" {
  name        = "${var.env}-hdc-eks-sg"
  vpc_id      = aws_vpc.main.id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ——————————————————————————————
# Kubernetes Provider & Helm
# ——————————————————————————————
data "aws_eks_cluster" "hdc" {
  name = aws_eks_cluster.hdc.name
}

data "aws_eks_cluster_auth" "hdc" {
  name = aws_eks_cluster.hdc.name
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.hdc.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.hdc.certificate_authority[0].data)
  token                  = data.aws_eks_cluster_auth.hdc.token
}

provider "helm" {
  kubernetes {
    host                   = data.aws_eks_cluster.hdc.endpoint
    cluster_ca_certificate = base64decode(data.aws_eks_cluster.hdc.certificate_authority[0].data)
    token                  = data.aws_eks_cluster_auth.hdc.token
  }
}

# Install Helm chart
resource "helm_release" "hardwareless_ai" {
  name       = "hardwareless-ai"
  namespace  = "hardwareless-ai"
  repository = "./deploy/helm/hardwareless-ai"
  chart      = "./deploy/helm/hardwareless-ai"
  version    = "0.3.0"
  wait       = true
  
  set {
    name  = "image.tag"
    value = var.image_tag
  }
  
  set {
    name  = "replicaCount"
    value = var.node_count
  }
  
  set {
    name  = "config.REDIS_URL"
    value = "redis://${aws_elasticache_cluster.hdc.cache_nodes[0].address}:6379"
  }
  
  set {
    name  = "secrets.REQUEST_SIGNING_SECRET"
    value = var.request_signing_secret
  }
}

# Outputs
output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.hdc.endpoint
}

output "redis_endpoint" {
  description = "Redis endpoint"
  value       = aws_elasticache_cluster.hdc.cache_nodes[0].address
}

output "helm_release" {
  description = "Helm release name"
  value       = helm_release.hardwareless_ai.name
}
