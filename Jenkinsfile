pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                git credentialsId: 'ravi2_ecs_worker_pkey', url: 'git@github.com:ravimails2004/ecs-worker-node-management.git'
                sh "ls"
            }

            post {
                success {
                    sh "echo  source code checkout successfull"
                }
            }
        }
    }
}
