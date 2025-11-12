# relx - Release eXtension for PYthon

`relx` is a command-line interface (CLI) tool designed to assist with release management tasks within the SUSE ecosystem, particularly interacting with Open Build Service (OBS) and Internal Build Service (IBS). It provides subcommands for managing artifacts, requests, reviews, packages, and users.

## Installation



To install `relx`, ensure you have Python 3.6 or newer installed.



From the project's root directory (where `pyproject.toml` is located), you can install it in one of the following ways:



1.  **Install in editable mode (for development):**

    ```bash

    # with pip

    pip install -e .

    # with uv

    uv pip install -e .

    ```

    This allows you to make changes to the source code and have the changes reflected immediately without reinstallation.



2.  **Install as a regular package:**

    ```bash

    # with pip

    pip install .

    # with uv

    uv pip install .

    ```



## Usage



Once installed, you can use the `relx` command.



*   **Get general help:**

    ```bash

    relx --help

    ```



*   **Subcommands:**

    `relx` includes several subcommands: `artifacts`, `requests`, `reviews`, `packages`, and `users`. To get help for a specific subcommand, use:

    ```bash

    relx <subcommand> --help

    # Example:

    # relx artifacts --help

    ```



*   **Common arguments:**

    The main `relx` command also accepts global arguments like `--osc-instance` and `--osc-config`.



## Configuration



`relx` uses a `config.lua` file for its configuration. An example configuration file is provided at `config_files/config.lua` within this repository.



To use `relx`, you should copy this example configuration file to your user configuration directory. By default, `relx` looks for `config.lua` in `~/.config/relx/`.



1.  **Copy the example configuration:**

    ```bash

    mkdir -p ~/.config/relx/

    cp config_files/config.lua ~/.config/relx/config.lua

    ```



2.  **Customize the configuration:**

    Edit `~/.config/relx/config.lua` to match your environment and preferences. Key sections include:

    *   `common`: General settings like `api_url`, `default_project`, and `debug` mode.

    *   `artifacts`: Configuration for listing artifacts, including repository names and patterns.

    *   `packages`: Settings related to package information, such as `default_productcomposer`.



3.  **`CONFIG_DIR` Environment Variable (Optional):**

    If you prefer to store your `config.lua` in a different location, you can set the `CONFIG_DIR` environment variable to point to that directory. For example:

    ```bash

    export CONFIG_DIR=/path/to/your/custom_config_directory

    ```

    If `CONFIG_DIR` is set, `relx` will use that path instead of the default `~/.config/relx/`.



## Development



### Linting and Formatting



This project uses `ruff` for linting and formatting. To ensure code quality and consistency, please run the following commands before submitting any changes:



*   **Run the linter:**

    ```bash

    # with ruff

    ruff check .

    # with uv

    uv run ruff check .

    ```



*   **Run the formatter:**

    ```bash

    # with ruff

    ruff format .

    # with uv

    uv run ruff format .

    ```


