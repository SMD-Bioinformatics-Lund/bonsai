Deployment into a production environment
========================================

The following should be done when deploying Bonsai to a production environment.

1. Change the SECRET_KEY variable in the Bonsai app and API configuration.
Use a production-ready WSGI server such as gunicorn instead of the default Flask development server.
2. Configure the BONSAI_API_URL in the frontend config or set it as an environmental variable. 
3. It should be set to the URL where you host the Bonsai API.

You should use SSL certificates in a production environment to protect the data sent from being intercepted. We also recommend enabling authentication to your Mongo database and setting up specific accounts for database administrators and software to protect your data. See the `Mongo documentation <https://www.mongodb.com/docs/manual/security/>`_ for more information on authentication and authorization mechanisms.