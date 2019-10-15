import ovh


def get_ovh_client(config):
    ovh_config = config["ovh"]
    ovh_client = ovh.Client(
        endpoint=ovh_config["endpoint"],
        application_key=ovh_config["application_key"],
        application_secret=ovh_config["application_secret"],
        consumer_key=ovh_config["consumer_key"],
    )

    return ovh_client
