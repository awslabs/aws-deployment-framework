OUTPUT=$(ls cdk.out/*template.json)
cdk --version

cdk synth
for file in $OUTPUT; do
  cdk deploy $(basename $file .template.json) --require-approval="never"
done