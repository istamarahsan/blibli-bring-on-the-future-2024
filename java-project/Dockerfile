FROM maven:3-eclipse-temurin-17 AS build  
COPY src /usr/src/app/src  
COPY pom.xml /usr/src/app  
RUN mvn -f /usr/src/app/pom.xml clean package

FROM eclipse-temurin:17
COPY --from=build /usr/src/app/target/app.jar /usr/app/app.jar  
EXPOSE 8080  
CMD ["java","-jar","/usr/app/app.jar"]  