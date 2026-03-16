pipeline {
    agent any

    environment {
        AWS_ACCOUNT_ID = credentials('aws-account-id')
        AWS_REGION     = 'us-west-2'
        IMAGE_NAME     = 'log-correlation-server'
        ECR_REPO       = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${IMAGE_NAME}"
        K8S_NAMESPACE  = 'log-correlation'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    env.IMAGE_TAG = "${env.BUILD_NUMBER}-${env.GIT_COMMIT?.take(7) ?: 'unknown'}"
                }
                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
            }
        }

        stage('Push to ECR') {
            steps {
                sh """
                    aws ecr get-login-password --region ${AWS_REGION} \
                      | docker login --username AWS --password-stdin ${ECR_REPO.split('/')[0]}

                    aws ecr describe-repositories --repository-names ${IMAGE_NAME} --region ${AWS_REGION} 2>/dev/null \
                      || aws ecr create-repository --repository-name ${IMAGE_NAME} --region ${AWS_REGION}

                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${ECR_REPO}:${IMAGE_TAG}
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${ECR_REPO}:latest
                    docker push ${ECR_REPO}:${IMAGE_TAG}
                    docker push ${ECR_REPO}:latest
                """
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                sh """
                    kubectl apply -f k8s/namespace.yaml

                    kubectl -n ${K8S_NAMESPACE} set image deployment/log-correlation \
                        log-correlation=${ECR_REPO}:${IMAGE_TAG}

                    kubectl -n ${K8S_NAMESPACE} rollout status deployment/log-correlation --timeout=120s
                """
            }
        }
    }

    post {
        success {
            echo "Deployed ${ECR_REPO}:${IMAGE_TAG} to ${K8S_NAMESPACE}"
        }
        failure {
            echo 'Deployment failed.'
        }
        always {
            sh "docker rmi ${IMAGE_NAME}:${IMAGE_TAG} || true"
            sh "docker rmi ${ECR_REPO}:${IMAGE_TAG} || true"
        }
    }
}
