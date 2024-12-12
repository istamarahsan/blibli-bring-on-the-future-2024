pipeline {
    agent any
    stages {
        stage('Setup') {
            steps {
                sh 'trivy image --download-db-only'
                sh 'go install github.com/CycloneDX/cyclonedx-gomod/cmd/cyclonedx-gomod@latest'
            }
        }
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/istamarahsan/blibli-bring-on-the-future-2024.git'
            }
        }
        stage('Projects') {
            parallel {
                stage ('Go') {
                    steps {
                        sh 'cd go-project && go build -o pb.exe && cyclonedx-gomod mod -assert-licenses=true -licenses=true -output build-bom.xml'
                        sh 'cd go-project && docker build -t go-project . && trivy image --scanners vuln --format cyclonedx --output container-bom.json go-project'
                    }
                    post {
                        success {
                            archiveArtifacts 'go-project/pb.exe'
                            archiveArtifacts 'go-project/build-bom.xml'
                            archiveArtifacts 'go-project/container-bom.json'
                            dependencyTrackPublisher artifact: 'go-project/build-bom.xml', projectName: 'go-project', projectVersion: '1.0', synchronous: false, projectProperties: [tags: ['level=build']]
                            dependencyTrackPublisher artifact: 'go-project/container-bom.json', projectName: 'go-project-container', projectVersion: '1.0', synchronous: false, projectProperties: [tags: ['level=container']]
                        }
                    }
                }
                stage ('Java') {
                    steps {
                        sh 'cd java-project && mvn clean package'
                        sh 'cd java-project && docker build -t java-project . && trivy image --scanners vuln --format cyclonedx --output target/container-bom.json java-project'
                    }
                    post {
                        success {
                            archiveArtifacts 'java-project/target/*.jar'
                            archiveArtifacts 'java-project/target/bom.json'
                            dependencyTrackPublisher artifact: 'java-project/target/bom.xml', projectName: 'java-project', projectVersion: '1.0-SNAPSHOT', synchronous: false, projectProperties: [tags: ['level=build']]
                            dependencyTrackPublisher artifact: 'java-project/target/container-bom.json', projectName: 'java-project-container', projectVersion: '1.0-SNAPSHOT', synchronous: false, projectProperties: [tags: ['level=container']]
                        }
                    }
                }
                stage ('Node') {
                    steps {
                        sh 'cd node-project && npm ci && npm run build && npm run sbom'
                        sh 'cd node-project && docker build -t node-project . && trivy image --scanners vuln --format cyclonedx --output build/container-bom.json node-project'
                    }
                    post {
                        success {
                            archiveArtifacts 'node-project/build/bom.xml'
                            archiveArtifacts 'node-project/build/container-bom.json'
                            dependencyTrackPublisher artifact: 'node-project/build/bom.xml', projectName: 'node-project', projectVersion: '1.0', synchronous: false, projectProperties: [tags: ['level=build']]
                            dependencyTrackPublisher artifact: 'node-project/build/container-bom.json', projectName: 'node-project-container', projectVersion: '1.0', synchronous: false, projectProperties: [tags: ['level=container']]
                        }
                    }
                }
            }
        }
    }
}
