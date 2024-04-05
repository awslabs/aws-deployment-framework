import { App, Stack, Duration } from 'aws-cdk-lib';
import { aws_lambda as lambda, aws_events as events, aws_events_targets as targets } from 'aws-cdk-lib';

import fs = require('fs');

export class LambdaCronStack extends Stack {
  constructor(app: App, id: string) {
    super(app, id);

    const lambdaFn = new lambda.Function(this, 'Singleton', {
      code: new lambda.InlineCode(
        fs.readFileSync('handler.py', { encoding: 'utf-8' }),
      ),
      handler: 'index.main',
      timeout: Duration.seconds(300),
      runtime: lambda.Runtime.PYTHON_3_12
    });
    // Run every day at 6PM UTC
    // See https://docs.aws.amazon.com/lambda/latest/dg/tutorial-scheduled-events-schedule-expressions.html
    const rule = new events.Rule(this, 'Rule', {
      schedule: events.Schedule.expression('cron(0 18 ? * MON-FRI *)')
    });
    rule.addTarget(new targets.LambdaFunction(lambdaFn));
  }
}

const app = new App();
new LambdaCronStack(app, 'LambdaCronExample');
app.synth();
