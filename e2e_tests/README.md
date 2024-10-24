# Bonsai end-to-end tests

The e2e tests uses a standalone [[Selenium chrome dirver](https://github.com/SeleniumHQ/docker-selenium)] agains a small collection of test samples located [[./e2e_tests/fixtures/samples]].

## Run tests

Run the test suite with the following command.

```bash
docker-compose -f docker-compose.yml -f docker-compose.e2e_test.yml run e2e-tests
```

This will bootstrap Bonsai by creating an admin user and a regular user, samples groups and index the database. It will populate the database with a collection of *Staphyloccous aureus* and *Mycobacterium tuberculosis*. The demo users have the following login credentials.

| Username | Password | Role  |
|----------|----------|-------|
| user     | user     | user  |
| admin    | admin    | admin |

In case your docker-compose version does'nt support [healthchecks](https://docs.docker.com/reference/compose-file/services/#healthcheck), Bonsai can be manually setup using the following steps, 

```bash
# 1. Start the containers.
docker-compose -f docker-compose.yml -f docker-compose.e2e_test.yml run --rm e2e-tests /bin/bash

# 2. Open the api log and check when the api is running.
#    Creating users and groups can take some time.
docker-compose -f docker-compose.yml -f docker-compose.e2e_test.yml logs --tail 40 --follow api

# 3. Load test samples from the e2e_test container (created in step 1).
bash /home/worker/load_test_samples.sh

# 4. Run test with pytest
pytest /home/worker/app/tests/
```

## Resources

- [Selenium python documentation](https://selenium-python.readthedocs.io/)
- [docker-compose documentation](https://docs.docker.com/reference/compose-file)