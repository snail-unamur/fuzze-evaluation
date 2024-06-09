# Fuzze

Fuzzee is a grammar based fuzzer for the Odoo web interface.

## Installation

To install the tool, the build script can be used. Run the following command to install the tool as a module in the current user's profile:

```pwsh
pwsh ./build.ps1
```

## Run the evaluation

To make mutants of a tour, several scripts are available in the `scripts` directory. Each script is a stub for the main flow tour using each strategy of the tool.

After the mutants are generated, simply run odoo using the config file `odoo_config.cfg` (made using the template) and add the argument `--test-tags fuzze` to run the tests.
