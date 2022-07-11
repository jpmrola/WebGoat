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
        jdk 'jdk17'
    }
    environment {
        SERVER_ADDR = '192.168.128.54'
        SCAN_URL_SITE = 'http://192.168.128.54:30680'
        SCAN_URL_YAML = 'http://192.168.128.54:30680/WebGoat'
        SCAN_URL_PYTHON = 'http://192.168.128.54:30680/WebGoat/login'
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
                sh '''sed -i "s/0.0.0.0/${SERVER_ADDR}/" ${WORKSPACE}/docker/start.sh'''
                sh '''cat ${WORKSPACE}/docker/start.sh'''
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
//        stage('Snyk analysis') {
//            steps {
//                catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
//                    snykSecurity(
//                    snykInstallation: 'snyk',
//                    snykTokenId: 'snyk',
//                    additionalArguments: '--debug --all-projects'
//                    )
//                }
//            }
//        }
        stage('Snyk Maven Scan') {
            failFast true
                environment {
                    SNYK_TOKEN = credentials('snyk-api')
                }	
            parallel {
                stage('Snyk Open-Source scan') {
                    steps {
                        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                            container('snyk-maven') {
                                sh '''
                                    snyk auth ${SNYK_TOKEN}
                                    snyk test --json --json-file-output=maven-results.json \
                                    --debug 
                                    snyk-to-html -i maven-results.json -o maven-results.html
                                    '''
                            }
                        }
                    }
                }
                stage('Snyk Code scan') {
                    steps {
                        container('snyk-docker') {
                            catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                                sh '''
                                    snyk auth ${SNYK_TOKEN}
                                    snyk code test --json --json-file-output=code-results.json \
                                    --debug 
                                    snyk-to-html -i code-results.json -o code-results.html
                                    '''
                            }
                        }
                    }
                }
                stage('Snyk Docker scan') {
                    steps {
                        container('snyk-docker') {
                            catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                                sh '''
                                    snyk auth ${SNYK_TOKEN}
                                    snyk container test --json --json-file-output=docker-results.json \
                                    jrolaubi/webgoat-tese \
                                    --file=`pwd`/docker/Dockerfile  
                                    snyk-to-html -i docker-results.json -o docker-results.html
                                    '''
                            }
                        }
                    }
                }
            }
        }
        stage('Move Report Files') {
            steps {
                container('snyk-maven') {
                    sh '''
                        mkdir ${WORKSPACE}/snyk-reports
                        mv ${WORKSPACE}/maven-results.* ${WORKSPACE}/snyk-reports
                        mv ${WORKSPACE}/code-results.* ${WORKSPACE}/snyk-reports
                        mv ${WORKSPACE}/docker-results.* ${WORKSPACE}/snyk-reports
                        '''
                }
            }
        }
        stage('Ansible playbook') {
            steps {
                ansiblePlaybook( 
                playbook: '${WORKSPACE}/ansible/deploy.yml',
                inventory: '/home/jenkins/ansible/inventory')
            }
        }
        stage('ZAP scan') {
            environment {
                WEBGOAT_CREDENTIALS = credentials('webgoat')
            }
            steps {
                timeout(time: 30, unit: 'SECONDS') {
                    waitUntil {
                        script {
                            try {
                                def response = httpRequest "${SCAN_URL_YAML}/registration"
                                return (response.status == 200)
                            }
                            catch (exception) {
                                 return false
                            }
                        }
                    }
                }
                script {
                    container(name: 'zap', shell: '/bin/sh') {
                        sh '''#!/bin/sh
                        export PATH=/zap:$PATH
                        mkdir /zap/wrk
                        mv ${WORKSPACE}/zap/zap.yml /zap/zap.yml
                        mv ${WORKSPACE}/zap/createAccount.py /zap/createAccount.py
                        sed -i "s,REPLACE_SITE,${SCAN_URL_SITE}," /zap/zap.yml
                        sed -i "s,REPLACE,${SCAN_URL_YAML}," /zap/zap.yml
                        python3 /zap/createAccount.py ${SCAN_URL_YAML}/register.mvc ${WEBGOAT_CREDENTIALS_USR} ${WEBGOAT_CREDENTIALS_PSW}
                        /zap/zap.sh -cmd -autorun zap.yml
                        cp -r /zap/wrk ${WORKSPACE}/zap-report
                        '''
//                        chmod +x -R ${env.WORKSPACE}
//                        /zap/zap-full-scan.py -r index.html -t ${SCAN_URL_PYTHON} || return_code=$?
//                        echo "exit value was  - " $return_code

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
                reportDir: './zap-report',
                reportFiles: 'index.html',
                reportName: 'OWASP Zed Attack Proxy'
            ]
            publishHTML target: [
                allowMissing: false,
                alwaysLinkToLastBuild: false,
                keepAll: true,
                reportDir: './snyk-reports',
                reportFiles: 'docker-results.html',
                reportName: 'Snyk Docker results'
            ]
            publishHTML target: [
                allowMissing: false,
                alwaysLinkToLastBuild: false,
                keepAll: true,
                reportDir: './snyk-reports',
                reportFiles: 'code-results.html',
                reportName: 'Snyk Code results'
            ]
            publishHTML target: [
                allowMissing: false,
                alwaysLinkToLastBuild: false,
                keepAll: true,
                reportDir: './snyk-reports',
                reportFiles: 'maven-results.html',
                reportName: 'Snyk Maven results'
            ]
        }
    }
}
