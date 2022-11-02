aws ecr get-login-password --region us-west-1 | docker login --username AWS --password-stdin 862592418544.dkr.ecr.us-west-1.amazonaws.com
docker build -t dothething-google-token-sign-in-handler .
docker tag dothething-google-token-sign-in-handler:latest 862592418544.dkr.ecr.us-west-1.amazonaws.com/dothething-google-token-sign-in-handler:latest
docker push 862592418544.dkr.ecr.us-west-1.amazonaws.com/dothething-google-token-sign-in-handler:latest
