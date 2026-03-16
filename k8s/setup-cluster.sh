#!/usr/bin/env bash
set -euo pipefail
#
# One-time cluster setup for the log-correlation service.
#
# This script creates:
#   1. The K8s namespace
#   2. ECR image pull secret (so the cluster can pull from your private ECR)
#   3. OpenSearch credentials secret
#   4. Initial deployment + service
#
# Prerequisites:
#   - kubectl configured and pointing at your cluster
#   - aws CLI configured with permissions for ECR
#
# Usage:
#   AWS_ACCOUNT_ID=123456789012 \
#   AWS_REGION=us-west-2 \
#   OPENSEARCH_URL=https://app-opensearch-dev.interface.ai \
#   OPENSEARCH_USERNAME=support-user \
#   OPENSEARCH_PASSWORD='your-password' \
#   ./k8s/setup-cluster.sh
#

AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:?Set AWS_ACCOUNT_ID}"
AWS_REGION="${AWS_REGION:-us-west-2}"
NAMESPACE="log-correlation"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

OPENSEARCH_URL="${OPENSEARCH_URL:?Set OPENSEARCH_URL}"
OPENSEARCH_USERNAME="${OPENSEARCH_USERNAME:?Set OPENSEARCH_USERNAME}"
OPENSEARCH_PASSWORD="${OPENSEARCH_PASSWORD:?Set OPENSEARCH_PASSWORD}"
OPENSEARCH_SSL_VERIFY="${OPENSEARCH_SSL_VERIFY:-false}"

echo "==> Creating namespace: ${NAMESPACE}"
kubectl apply -f k8s/namespace.yaml

# --- ECR pull secret ---
# EKS nodes in the SAME AWS account usually pull from ECR automatically
# via the node IAM role. If that works for you, you can skip this step.
#
# For cross-account ECR or clusters without node IAM permissions,
# create a docker-registry secret from the ECR login token:
echo "==> Creating ECR image pull secret..."
ECR_TOKEN=$(aws ecr get-login-password --region "${AWS_REGION}")
kubectl -n "${NAMESPACE}" create secret docker-registry ecr-pull-secret \
  --docker-server="${ECR_REGISTRY}" \
  --docker-username=AWS \
  --docker-password="${ECR_TOKEN}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo ""
echo "    NOTE: ECR tokens expire after 12 hours. For long-term use, either:"
echo "      a) Use the EKS node IAM role (recommended for same-account EKS)"
echo "      b) Set up a CronJob to refresh the ecr-pull-secret periodically"
echo "      c) Use the Amazon ECR Credential Helper"
echo ""

# --- OpenSearch credentials ---
echo "==> Creating OpenSearch credentials secret..."
kubectl -n "${NAMESPACE}" create secret generic opensearch-credentials \
  --from-literal=OPENSEARCH_URL="${OPENSEARCH_URL}" \
  --from-literal=OPENSEARCH_USERNAME="${OPENSEARCH_USERNAME}" \
  --from-literal=OPENSEARCH_PASSWORD="${OPENSEARCH_PASSWORD}" \
  --from-literal=OPENSEARCH_SSL_VERIFY="${OPENSEARCH_SSL_VERIFY}" \
  --dry-run=client -o yaml | kubectl apply -f -

# --- Deploy ---
echo "==> Applying deployment and service..."
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

echo ""
echo "==> Setup complete!"
echo "    Check status:  kubectl -n ${NAMESPACE} get pods,svc"
echo "    Port-forward:  kubectl -n ${NAMESPACE} port-forward svc/log-correlation 8765:80"
echo "    Open:          http://localhost:8765"
