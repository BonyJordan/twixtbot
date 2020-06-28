#! /bin/bash
for host in `aws ec2 describe-instances | awk '/INSTANCE/ {print $16}'`
do
    echo $host
    ssh -i ~/.ssh/aws-twixy.pem -l ec2-user $host "$@"
done
