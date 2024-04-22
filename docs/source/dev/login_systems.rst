Login systems
=============

Bonsai currently support two login systems, LDAP authentication and a simple username and password authentication. These login sytems are mutually exclusive so by chosing one the other is being disabled.

Simple authentication
---------------------

The default authentication method is logging using a username and password. The password is being salted and stored in the mongo database.

LDAP authentication
-------------------

Authentication can be made against an institutional LDAP3 server. You need an existing LDAP authentication server to user this authentication method. The users need to have an account in Bonsai in addition to having an entry on the LDAP server, because the user roles are determined from the Bonsai account.

Use either the API CLI or the Admin panel to create a new user.

The LDAP3 server connection is configured using environmental variables. At minimum you need to configure the following variables.

.. csv-table:: Minimal configuration :rst:dir:`csv-table`
   :header: "Variable name", "Description"

   "LDAP_HOST",               "Server host or IP"
   "LDAP_PORT",               "Server port"
   "LDAP_BASE_DN",            "Base distinguished name (DN) for searching the server"
   "LDAP_BIND_DN",            "Admin bind DN"
   "LDAP_SECRET",             "Optional password for the admin bind DN"
   "LDAP_SEARCH_ATTR",        "Attribute to validate username against"

See the `config.py` for all variables that can be configured using environment variables.

Example configuration
~~~~~~~~~~~~~~~~~~~~~
Here is a example of an LDAP based authentication configuration using docker-compose. We use a demo `LDAP server <https://github.com/rroemhild/docker-test-openldap>`_ populated with Futurama characters.

.. code-block:: yaml
   :caption: Example configuration

   version: '3.9'
   # usage:
   # (sudo) docker-compose up -d
   # (sudo) docker-compose down
   services: 
      mongodb:
         image: mongo:4.4.22
         ports:
            - "8813:27017"
         expose:
            - "27017"
         volumes:
            - "./volumes/mongodb:/data/db"
         networks:
            - bonsai-net

      redis:
         image: redis:7.0.10
         networks:
            - bonsai-net

      openldap:
         image: ghcr.io/rroemhild/docker-test-openldap:master
         container_name: openldap
         ports:
            - "10389:10389"
            - "10636:10636"
         networks:
            - bonsai-net
         privileged: true

      api:
         container_name: bonsai_api
         build: 
            context: api
            network: host
         depends_on:
            - mongodb
         ports: 
            - "8811:8000"
         environment:
            - DB_HOST=mongodb
            - REDIS_HOST=redis
            - LDAP_HOST=openldap
            - LDAP_PORT=10389
            - LDAP_BIND_DN=cn=admin,dc=planetexpress,dc=com
            - LDAP_SECRET=GoodNewsEveryone
            - LDAP_BASE_DN=dc=planetexpress,dc=com
            - LDAP_USER_LOGIN_ATTR=mail
            - LDAP_USE_SSL=false
            - LDAP_USE_TLS=false
         networks:
            - bonsai-net
         command: "uvicorn app.main:app --reload --log-level debug --host 0.0.0.0"

      app:
         container_name: bonsai_app
         build: 
            context: frontend
            network: host
         depends_on:
            - mongodb
            - api
         ports: 
            - "8812:5000"
         environment:
            - FLASK_APP=app.app:create_app
            - FLASK_ENV=development 
            - "BONSAI_API_URL=http://mtlucmds2.lund.skane.se:8811"
         networks:
            - bonsai-net
         command: "flask run --debug --host 0.0.0.0"

   networks:
      bonsai-net:
         driver: bridge
         ipam:
            driver: default
            config:
            - subnet: 172.0.30.0/24