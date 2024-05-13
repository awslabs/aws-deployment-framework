# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

FROM public.ecr.aws/docker/library/node:current-alpine
WORKDIR /app
COPY . .
RUN npm install
EXPOSE 3000
ENTRYPOINT  ["npm", "start"]
