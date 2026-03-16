#!/usr/bin/env bash
set -euo pipefail
#
# Manual deploy / rollout trigger.
#
# Jenkins handles the full build-push-deploy cycle via Jenkinsfile.
# Use this script for manual operations:
#
#   ./deploy.sh apply          Apply all K8s manifests (initial deploy)
#   ./deploy.sh rollout        Trigger a rolling restart
#   ./deploy.sh status         Show pod and service status
#   ./deploy.sh logs           Tail logs from running pods
#   ./deploy.sh port-forward   Forward localhost:8765 to the service
#

NAMESPACE="log-correlation"
ACTION="${1:-help}"

case "$ACTION" in
  apply)
    echo "==> Applying all manifests..."
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/deployment.yaml
    kubectl apply -f k8s/service.yaml
    echo "==> Done. Run: ./deploy.sh status"
    ;;
  rollout)
    echo "==> Triggering rolling restart..."
    kubectl -n "$NAMESPACE" rollout restart deployment/log-correlation
    kubectl -n "$NAMESPACE" rollout status deployment/log-correlation --timeout=120s
    ;;
  status)
    echo "==> Pods:"
    kubectl -n "$NAMESPACE" get pods -o wide
    echo ""
    echo "==> Service:"
    kubectl -n "$NAMESPACE" get svc
    echo ""
    echo "==> Recent events:"
    kubectl -n "$NAMESPACE" get events --sort-by='.lastTimestamp' | tail -10
    ;;
  logs)
    kubectl -n "$NAMESPACE" logs -l app.kubernetes.io/name=log-correlation --tail=100 -f
    ;;
  port-forward)
    echo "==> Forwarding localhost:8765 -> svc/log-correlation:80"
    echo "    Open http://localhost:8765"
    kubectl -n "$NAMESPACE" port-forward svc/log-correlation 8765:80
    ;;
  help|*)
    echo "Usage: ./deploy.sh {apply|rollout|status|logs|port-forward}"
    echo ""
    echo "  apply         Apply all K8s manifests"
    echo "  rollout       Trigger a rolling restart of pods"
    echo "  status        Show pods, services, and recent events"
    echo "  logs          Tail logs from running pods"
    echo "  port-forward  Forward localhost:8765 to the cluster service"
    echo ""
    echo "For initial setup (secrets, ECR pull), run: ./k8s/setup-cluster.sh"
    echo "For full CI/CD builds, use the Jenkinsfile."
    ;;
esac
