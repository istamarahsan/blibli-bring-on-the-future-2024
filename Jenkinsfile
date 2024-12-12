pipeline {
    agent any

    tools {
        maven "M3"
        go '1.23'
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/istamarahsan/blibli-bring-on-the-future-2024.git'
            }
        }
        parallel {
            stage ('Go') {
                steps {
                    sh 'cd go-project && go build -o pb.exe && chmod +x ./cyclonedx-gomod/cyclonedx-gomod && ./cyclonedx-gomod/cyclonedx-gomod mod -assert-licenses=true -licenses=true -verbose=true -output bom.xml'   
                }
                post {
                    success {
                        archiveArtifacts 'go-project/pb.exe'
                        archiveArtifacts 'go-project/bom.xml'
                        dependencyTrackPublisher artifact: 'go-project/bom.xml', projectName: 'go-project', projectVersion: '1.0', synchronous: false, projectProperties: [tags: ['level=build']]
                    }
                }
            }
            stage ('Java') {
                steps {
                    sh 'cd java-project && mvn clean package'
                }
                post {
                    success {
                        archiveArtifacts 'java-project/target/*.jar'
                        archiveArtifacts 'java-project/target/bom.json'
                        dependencyTrackPublisher artifact: 'java-project/target/bom.xml', projectName: 'java-project', projectVersion: '1.0-SNAPSHOT', synchronous: false, projectProperties: [tags: ['level=build']]
                    }
                }
            }
            stage ('Node') {
                steps {
                    nodejs(nodeJSInstallationName: '22') {
                        sh 'cd node-project && npm ci && npm run build && npm run sbom'
                    }
                }
                post {
                    success {
                        archiveArtifacts 'node-project/build/bom.xml'
                        dependencyTrackPublisher artifact: 'node-project/build/bom.xml', projectName: 'node-project', projectVersion: '1.0', synchronous: false, projectProperties: [tags: ['level=build']]
                    }
                }
            }
        }
        
    }
}
