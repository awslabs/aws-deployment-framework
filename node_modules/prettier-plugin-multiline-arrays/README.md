# prettier-plugin-multiline-arrays

Prettier plugin to force array elements to wrap onto new lines, even when there's only one element (if you so specify). Supports control of how many elements appear on each line. Insert leading new lines or trailing commas to manually force array wrapping.

TypeScript, JavaScript, and JSON files are officially supported (others may still work).

[Please file issues in the GitHub repo](https://github.com/electrovir/prettier-plugin-multiline-arrays/issues/new) and include code examples if you come across formatting errors.

## Usage

Add this config to your prettierrc file:

<!-- example-link: src/readme-examples/prettier-options.example.ts -->

```TypeScript
module.exports = {
    plugins: [
        // relative paths are usually required, in my experience, so Prettier can find the plugin
        './node_modules/prettier-plugin-multiline-arrays',
    ],
};
```

The order of your plugins array is very important, so if you have other plugins and they don't work initially, try rearranging them. For an example, check out the plugin ordering for this package's Prettier config: [`./prettierrc.js`](https://github.com/electrovir/virmator/blob/5d6503bfc31bd44daee6fec1c6e8024e7bc93b84/base-configs/base-prettierrc.js#L30-L37)

## Options

This plugin provides two new options for your Prettier config:

-   **`multilineArraysWrapThreshold`**: This should be set to a single number which controls when arrays wrap. If an array has _more_ elements than the number specified here, it will be forced to wrap. This option defaults to `-1`, which indicates that no automatic wrapping will take place. Example JSON: `"multilineArraysWrapThreshold": 3,`. To override this option for an individual array, precede the array with a comment like so: `// prettier-multiline-arrays-next-threshold: 4`.
-   **`multilineArraysLinePattern`**: This should be set to a string which contains a space separated list of numbers. These numbers allow fine grained control over how many elements appear in each line. The pattern will repeat if an array has more elements than the pattern. See the `Examples` section for how this works. This defaults to just `1`, which indicates all array lines have just a single element. Example: `"multilineArraysLinePattern": "2 1"`, which means the first line will have 2 elements, the second will have 1, the third will have 2, the fourth will have 1, and so on. If set, _this option overrides Prettier's default wrapping; multiple elements on one line will not be wrapped even if they don't fit within the column count._ To override this option for an array, precede the array with a comment like so: `// prettier-multiline-arrays-next-line-pattern: 2 1`.

## Comment overrides

-   Add a comment starting with `prettier-multiline-arrays-next-threshold:` followed by a single number to control `multilineArraysWrapThreshold` for an array on the next line.
-   Add a comment starting with `prettier-multiline-arrays-next-line-pattern:` followed by a pattern of numbers to control `multilineArraysLinePattern` for an array on the next line.

To set a comment override for all arrays in a file following the comment, change `next` to `set`. Like so:

-   `prettier-multiline-arrays-set-threshold: 5`
-   `prettier-multiline-arrays-set-line-pattern: 2 1 3`

To later undo a `set` comment, use `prettier-multiline-arrays-reset`, which resets the options to whatever you have set in prettierrc, or the default values.

## Precedence

The precedence of forcing wrapping goes as follows:

1. Comments override all else
2. Manually forced wrapping (leading new lines, trailing commas) overrides configs and defaults
3. Your specific Prettier options override the defaults
4. The defaults are that no extra wrapping will be forced

## Examples

-   Not formatted:

    <!-- example-link: src/readme-examples/not-formatted.example.ts -->

    ```TypeScript
    // prettier-ignore
    export const myArray = ['a', 'b', 'c',]; // note the trailing comma which forces a wrap

    // prettier-ignore
    export const myCustomArray = [
            'a', 'b', 'c', 'd', 'e'] // note the leading new line which forces a wrap
    ```

-   Removing the `prettier-ignore` comments leads to formatting like this (with the default options):

    <!-- example-link: src/readme-examples/formatted.example.ts -->

    ```TypeScript
    export const myArray = [
        'a',
        'b',
        'c',
    ]; // note the trailing comma which forces a wrap

    export const myCustomArray = [
        'a',
        'b',
        'c',
        'd',
        'e',
    ]; // note the leading new line which forces a wrap
    ```

-   Use comment overrides to affect wrapping:

    <!-- example-link: src/readme-examples/formatted-with-comments.example.ts -->

    ```TypeScript
    // prettier-multiline-arrays-next-line-pattern: 2 1
    export const linePatternArray = [
        'a', 'b',
        'c',
        'd', 'e',
    ];

    // Even if this example had a leading new line or a trailing comma, it won't wrap because the
    // comment overrides that behavior.
    // prettier-multiline-arrays-next-threshold: 10
    export const highThresholdArray = ['a', 'b', 'c', 'd', 'e'];

    // this array doesn't fully wrap even though it exceeded the column width because the
    // "next-line-pattern" comment overrides Prettier's column width wrapping
    // prettier-multiline-arrays-next-line-pattern: 100
    export const superHighThresholdArray = [
        'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
    ];
    ```

## Compatibility

Tested to be compatible with the following plugins. It is likely compatible with many others as well. This plugin must be placed in the order specified below.

1. `prettier-plugin-toml`
2. `prettier-plugin-sort-json`
3. `prettier-plugin-packagejson`
4. this plugin must be placed here
5. `prettier-plugin-organize-imports`
6. `prettier-plugin-jsdoc`
7. `prettier-plugin-interpolated-html-tags`

## Dev

### Debugging

-   Set the `NEW_LINE_DEBUG` environment variable to something truthy before formatting to get extra debug output when formatting.
-   To debug in browser dev tools, run `npm run test:debug` and open Chrome's dev tools.
