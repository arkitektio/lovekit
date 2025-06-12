"""The core client for the kabinet service"""

from koil.composition import Composition


from lovekit.rath import LovekitRath


class Lovekit(Composition):
    """Kabinet Service Composition

    This context manager wraps all the necessary components to interact
    with a kabinet service. Kabinet needs only a graphql
    client to be able to interact with the service This is
    provided by the rath client.


    """

    rath: LovekitRath
