pipeline {
    agent any

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build') {
            steps {
                sh './scripts/up.sh'
            }
        }

        stage('Test') {
            steps {
                sh './scripts/test.sh'
            }
        }
    }

    post {
        always {
            sh './scripts/clean.sh'
        }
    }
}