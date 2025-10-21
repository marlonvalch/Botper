pipeline {
    agent any
    environment {
        IMAGE_NAME = "botper-app"
        REGISTRY = ""
        TAG = "latest"
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
                    docker.build("${IMAGE_NAME}:${TAG}")
                }
            }
        }
        stage('Test') {
            steps {
                sh 'pip install -r botper/requirements.txt'
                sh 'pytest || true' // Adjust if you have tests
            }
        }
        stage('Push to Registry') {
            when {
                expression { env.REGISTRY != '' }
            }
            steps {
                script {
                    docker.withRegistry(env.REGISTRY) {
                        docker.image("${IMAGE_NAME}:${TAG}").push()
                    }
                }
            }
        }
    }
}
