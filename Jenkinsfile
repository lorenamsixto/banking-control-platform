pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git branch -a'
            }
        }

        stage('Linter & Static Analysis') {
            steps {
                sh 'docker compose build backend frontend'
                sh 'docker compose run --rm backend flake8 sync'
                sh 'docker compose run --rm frontend npm run lint'
            }
        }

        stage('Unit Testing') {
            steps {
                sh 'docker compose up -d db'

                sh '''
                    docker compose run --rm backend \
                    pytest \
                    --cov=sync \
                    --cov-config=.coveragerc \
                    --cov-report=term-missing \
                    --cov-fail-under=80
                '''

                sh 'docker compose run --rm frontend npm run test'

                sh 'docker compose run --rm frontend npm run build'
            }
        }

        stage('Docker Build') {
            steps {
                sh 'docker compose build'
            }
        }
    }

    post {
        always {
            sh 'docker compose down -v --remove-orphans'
        }
    }
}