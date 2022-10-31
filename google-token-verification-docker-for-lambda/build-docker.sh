aws ecr get-login-password --region us-west-1 | docker login --username AWS --password-stdin 862592418544.dkr.ecr.us-west-1.amazonaws.com
docker build -t domino-google-token-verification .
docker tag domino-google-token-verification:latest 862592418544.dkr.ecr.us-west-1.amazonaws.com/domino-google-token-verification:latest
docker push 862592418544.dkr.ecr.us-west-1.amazonaws.com/domino-google-token-verification:latest
