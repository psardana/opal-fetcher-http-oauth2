# OPAL Fetcher for HTTP with OAuth2

Check out OPAL main repo [here](https://github.com/permitio/opal)

---

## What's in this repo?

An OPAL [custom fetch provider](https://docs.opal.ac/tutorials/write_your_own_fetch_provider) that enables fetching data over HTTP using OAuth2 authentication. This is particularly useful when you need to retrieve policy data from APIs that require OAuth2 client credentials flow for authentication.

This fetcher is:

- **A fully functional fetch provider for HTTP with OAuth2 authentication: Can be used by OPAL to fetch data from protected HTTP endpoints.**

---

## How to use this fetcher in your OPAL Setup

1. **Build a custom opal-client Docker image**<br><br>
    The official OPAL Docker image includes only the built-in fetch providers. To use this  fetcher, you need to create your own Dockerfile based on the official image and install this fetcher's package.<br><br>
  
    Your custom Dockerfile should look like this:

    ```dockerfile
    FROM permitio/opal-client:latest
    
    # Install dependencies for the fetcher
    RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
    
   COPY --chown=opal . /app/
    
   # Install the fetcher package
   RUN cd /app && python setup.py install --user
   RUN pip install --no-cache-dir -r /app/requirements.txt
    ```

2. **Build your custom opal-client container**<br><br>
    Assuming your Dockerfile is saved as `custom_client.Dockerfile`, build the Docker image:

    ```bash
    docker build -t yourcompany/opal-client -f custom_client.Dockerfile .
    ```

    Replace `yourcompany` with your organization's name or preferred namespace.<br><br>

3. **Configure OPAL to use the custom fetcher**<br><br>

    When running the OPAL client container, set the `OPAL_FETCH_PROVIDER_MODULES` environment variable to include this custom fetcher:
  
    ```makefile
    OPAL_FETCH_PROVIDER_MODULES=opal_common.fetcher.providers,opal_fetcher_http_oauth2.provider
    ```

    This tells OPAL where to find fetch providers. The list includes the built-in providers (`opal_common.fetcher.providers`) and the custom HTTP OAuth2 fetcher (`opal_fetcher_http_with_oauth2.provider`).<br><br>

4. **Configure your DataSourceEntry objects**<br><br>

    Your `DataSourceEntry` objects (either defined in `OPAL_DATA_CONFIG_SOURCES` or sent dynamically via the OPAL publish API) can now use this custom fetcher.<br><br>
  
    Example value for `OPAL_DATA_CONFIG_SOURCES` (formatted for readability):
  
    ```json
    {
      "config": {
       "entries": [
        {
          "url": "YOUR_HTTP_ENDPOINT",
          "config": {
           "fetcher": "OpalOAuth2HttpFetcher",
           "token_url": "YOUR_OAUTH_TOKEN_URL",
           "client_id": "YOUR_OAUTH_CLIENT_ID",
           "scope": "YOUR_OAUTH_SCOPE",
           "data_source_name": "YOUR_DATA_SOURCE_NAME"
          },
          "topics": ["TOPIC_NAME"],
          "dst_path": "YOUR_DST_PATH"
        }
       ]
      }
    }
    ```

    Explanation of the configuration:

    - `url`: The HTTP endpoint from which to fetch data.
    - `config`: Configuration specific to this fetcher, an instance of `OpalOAuth2HttpFetcherConfig`:
      - `fetcher`: Must be set to `"OpalOAuth2HttpFetcher"` to indicate the use of this custom fetcher.
      - `token_url`: The OAuth2 token endpoint URL to obtain the access token.
      - `client_id`: The client ID for OAuth2 authentication.
      - `scope`: (Optional) The scope for OAuth2 authentication.
      - `data_source_name`: A unique identifier for your data source, used to construct environment variable keys.
    - `topics`: Topics to associate with this data source entry.
    - `dst_path`: The destination path in the policy data store where the fetched data will be stored.
      <br><br>
5. **Set the client secret as an environment variable on the OPAL client**<br><br>

    The fetcher expects the client secret to be provided via an environment variable. The name of the environment variable is constructed using the `data_source_name` from the configuration, appended with `_OAUTH_CLIENT_SECRET`.<br><br>

    For example, if the `data_source_name` is `EMPLOYEE_DATA_SERVICE`, the environment variable should be named `EMPLOYEE_DATA_SERVICE_OAUTH_CLIENT_SECRET`.

    You must define this environment variable on the OPAL client. Here's how you can set it using Kubernetes secrets:

    ```yaml
    - name: EMPLOYEE_DATA_SERVICE_OAUTH_CLIENT_SECRET
      valueFrom:
       secretKeyRef:
        key: clientSecret
        name: secret-name
    ```

    Explanation:

    - `name`: The name of the environment variable (`EMPLOYEE_DATA_SERVICE_OAUTH_CLIENT_SECRET`).
    - `valueFrom`: Specifies that the value comes from a Kubernetes secret.
      - `secretKeyRef`:
        - `name`: The name of the Kubernetes secret (`secret-name`).
        - `key`: The key within the secret that contains the client secret (`clientSecret`).

    Ensure that this environment variable is available to the OPAL client container. If you're using Docker Compose or running the container directly, you can pass the environment variable using the `-e` flag or define it in your Docker Compose file.<br><br>

---

## 🛠 **Customization and Extension**

Feel free to customize and extend this fetcher to suit your specific needs

---

## 🤝 Contributing

Contributions are welcome! If you have ideas for improvements or find any issues, please open an issue or submit a pull request.

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.