FROM golang:1.21.6-alpine AS build

WORKDIR /build

COPY go.mod .
COPY go.sum .

RUN go mod download

COPY *.go .
COPY migrations/*.go ./migrations/

RUN CGO_ENABLED=0 go build -o dearearthpb

FROM alpine:3

RUN apk add --no-cache \
    unzip \
    ca-certificates

WORKDIR /pb

COPY --from=build /build/dearearthpb .

COPY ./migrations ./pb_migrations

COPY ./hooks ./pb_hooks

CMD ["sh", "-c", "/pb/dearearthpb serve --http=0.0.0.0:${PORT:-8080}"]