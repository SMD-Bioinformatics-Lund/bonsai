Frontend
========

The frontend is written in Flask and queries the API service to get data from the database.
Queries can be conducted from the python layer using functions defined in `bonsai.py`.
These functions can either be called in the view functions that determine how the individual pages should rendered or by calling entrypoints defined in the `api` blueprint.

Development setting
-------------------

To configure the frontend to run in _test_ mode set the environment variable `TESTING` to True which increases the log level and enables falsk debug mode.

.. code-block:: yaml
   :caption: Example of how to enable frontend testing mode.

   frontend:
     environment:
       - TESTING=True