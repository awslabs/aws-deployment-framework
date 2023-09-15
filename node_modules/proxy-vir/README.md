# proxy-vir

Creates a proxy based on multiple dynamically cascaded targets (meaning you can add or remove targets whenever you want) with dynamic proxy handler overriding (meaning you can modify how proxy handlers operate after the proxy has been created).

# Installation

```bash
npm i proxy-vir
```

# Usages

## Simple override

<!-- example-link: src/readme-examples/create-proxy.example.ts -->

```TypeScript
import {createWrappedMultiTargetProxy} from 'proxy-vir';

// something you imported from a 3rd party library that you want to wrap
const importedThing = {
    doThingA() {},
};

const thingWrapper = createWrappedMultiTargetProxy({
    initialTarget: importedThing,
});

// add a new override
thingWrapper.proxyModifier.addOverrideTarget({
    doThingA() {},
});
```
