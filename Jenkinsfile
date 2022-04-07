pipeline {
    triggers{
        githubPush()
    }
    agent {
        kubernetes {
            label 'kubeagent-webgoat'
        }
    }
    tools {
        maven 'maven'
        jdk 'openjdk17'
    }
    stages {
        stage('Clone repo') { 
            steps {
                checkout scm
            }
        }
        stage('Build project') { 
            steps {
                // sh '${WORKSPACE}/mvnw clean install -DskipTests'
                sh 'mvn clean install -DskipTests'
            }
        }
        stage('SonarQube analysis') {
            steps {
                script {
                    def scannerHome = tool 'sonarscanner';
                    withSonarQubeEnv('sonarqube-webgoat') { // If you have configured more than one global server connection, you can specify its name
                        sh '''mvn sonar:sonar \
                        -Dsonar.projectKey=webgoat\
                        -Dsonar.host.url=${SONAR_HOST_URL}\
                        -Dsonar.login=${SONAR_AUTH_TOKEN}'''
//                        sh '''${scannerHome}/bin/sonar-scanner \
//                        -Dsonar.language=java\
//                        -Dsonar.sources= . \
                    }
                }
            }
        }
        stage('Build and push image') { 
            environment {
                PATH        = "/busybox:$PATH"
                REGISTRY    = 'index.docker.io'
                REPOSITORY  = 'jrolaubi'
                IMAGE       = 'webgoat-tese'
            }
            steps {
                script {
                    container(name: 'kaniko', shell: '/busybox/sh') {
                    sh '''#!/busybox/sh
                    /kaniko/executor -f `pwd`/docker/Dockerfile -c `pwd`/docker --build-arg webgoat_version=8.2.0-SNAPSHOT --cache=true --destination=${REGISTRY}/${REPOSITORY}/${IMAGE}
                    '''
                    }
                }
            }
        }
        stage('Snyk analysis') {
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                    snykSecurity(
                    snykInstallation: 'snyk',
                    snykTokenId: 'snyk',
                    additionalArguments: '--debug'
                    )
                }
            }
        }
        stage('Ansible playbook') {
            steps {
                ansiblePlaybook( 
                playbook: '${WORKSPACE}/ansible/deploy.yml',
                inventory: '${WORKSPACE}/ansible/inventory')
            }
        }
        stage('ZAP scan') {
            steps {
                script {
                    container(name: 'zap', shell: '/bin/sh') {
                        sh '''#!/bin/sh
                        export PATH=/zap:$PATH
                        /zap/zap-baseline.py -r index.html -t http://10.110.0.5:30680/WebGoat || return_code=$?
                        echo "exit value was  - " $return_code
                        '''
                    }
                }
            }
        }
    }
    post {
        always {
            // publish html
            publishHTML target: [
                allowMissing: false,
                alwaysLinkToLastBuild: false,
                keepAll: true,
                reportDir: '/zap/wrk',
                reportFiles: 'index.html',
                reportName: 'OWASP Zed Attack Proxy'
            ]
        }
    }
}
