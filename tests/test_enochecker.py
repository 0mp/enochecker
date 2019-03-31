import logging

import pytest
import sys
import time

import enochecker
from enochecker import *


class CheckerExampleImpl(BaseChecker):

    def __init__(self, method=CHECKER_METHODS[0], address="localhost", team_name="Testteam",
                 round=1, flag="ENOFLAG", call_idx=0, max_time=30, port=9999,
                 fail=False):
        """
        An mocked implementation of a checker for testing purposes
        :param method: The method the checker uses
        :param fail: If and how
        """
        super(CheckerExampleImpl,self).__init__(method=method, address=address, team_name=team_name,
                         round=round, flag=flag, call_idx=call_idx, max_time=max_time,
                         port=port)
        self.logger.setLevel(logging.DEBUG)

    def store_flag(self):
        self.team_db["flag"] = self.flag

    def retrieve_flag(self):
        try:
            if not self.team_db["flag"] == self.flag:
                raise BrokenServiceException("Flag not found!")
        except KeyError:
            raise BrokenServiceException("Flag not correct!")

    def store_noise(self):
        self.team_db["noise"] = self.noise

    def retrieve_noise(self):
        try:
            if not self.team_db["noise"] == self.noise:
                raise BrokenServiceException("Noise not correct!")
        except KeyError:
            raise BrokenServiceException("Noise not found!")

    def havoc(self):
        raise OfflineException("Could not connect to team {} at {}:{} because this is not a real checker script."
                               .format(self.team_name, self.address, self.port))


def test_assert_equals():
    with pytest.raises(BrokenServiceException):
        assert_equals(1, 2)
    assert_equals(1, 1)
    assert_equals(u"test", b"test", autobyteify=True)
    if "test" == b"test":  # We ignore unicode stuff for python2...
        return
    with pytest.raises(BrokenServiceException) as ex:
        assert_equals("test", b"test", autobyteify=False, message="Fun")
    assert_equals(b"Fun", ex.value, autobyteify=True)


def test_conversions():
    assert isinstance(ensure_bytes("test"), bytes)
    assert isinstance(ensure_bytes(b"test"), bytes)
    assert isinstance(ensure_unicode("test"), type(u""))
    assert isinstance(ensure_unicode(b"test"), type(u""))
    assert ensure_unicode(ensure_bytes("test")) == u"test"


def test_assert_in():
    with pytest.raises(BrokenServiceException):
        assert_in("fun", "games")
    assert_in("fun", "fun and games")
    assert_in("quack", ["quack", "foo"])


def test_snake_caseify():
    assert snake_caseify("ThisIsATest") == "this_is_a_test"


def test_dict():
    db = enochecker.StoredDict(name="test")
    with pytest.raises(KeyError):
        test = db["THIS_KEY_WONT_EXIST"]

    db["test"] = "test"
    assert not db.is_locked("fun")
    db.lock("fun")
    assert db.is_locked("fun")
    db["fun"] = "fun"
    db.release("fun")
    db["fun"] = "fun2"
    db.persist()

    db.reload()
    assert db["test"] == "test"

    db2 = enochecker.StoredDict(name="test")
    assert db2["test"] == "test"

    assert len(db) > 0
    keys = [x for x in db.keys()]
    for key in keys:
        del db[key]
    db.persist()
    assert len(db) == 0


def test_parser_fail():
    with pytest.raises(SystemExit):
        CheckerExampleImpl(method=None)


def test_args():
    with pytest.raises(SystemExit):
        CheckerExampleImpl(method=None)

    with pytest.raises(SystemExit):
        parse_args()

    argv = [
        CHECKER_METHODS[0],
        "localhost",
        "TestTeam",
        "1",
        "ENOFLAG",
        "30",
        "0",
        "-p", "1337"
    ]
    args = parse_args(argv)
    assert args.method == argv[0]
    assert args.address == argv[1]
    assert args.team_name == argv[2]
    assert args.round == int(argv[3])
    assert args.flag == argv[4]
    assert args.max_time == int(argv[5])
    assert args.call_idx == int(argv[6])
    assert args.port == int(argv[8])


def test_checker_connections():
    # TODO: Check timeouts?
    text = "ECHO :)"
    port = serve_once(text)
    checker = CheckerExampleImpl(CHECKER_METHODS[0], port=port)
    assert checker.http_get("/").text == text

    # Give server time to shut down
    time.sleep(0.2)

    port = serve_once(text)
    checker = CheckerExampleImpl(CHECKER_METHODS[0], port=port)
    t = checker.connect()
    t.write(b"GET / HTTP/1.0\r\n\r\n")
    assert readline_expect(t, "HTTP")
    t.close()


def test_checker():
    flag = "ENOFLAG"
    noise = "buzzzz! :)"

    # It definitely shouldn't be allowed to run other existing functions
    assert CheckerExampleImpl(method="__init__").run() == Result.INTERNAL_ERROR

    CheckerExampleImpl(method="StoreFlag", flag=flag).run()
    assert CheckerExampleImpl().team_db["flag"] == flag
    CheckerExampleImpl(method="RetrieveFlag", flag=flag).run()

    CheckerExampleImpl(method="StoreNoise", flag=noise).run()
    assert CheckerExampleImpl().team_db["noise"] == noise
    CheckerExampleImpl(method="RetrieveNoise", flag=noise).run()

    assert CheckerExampleImpl(method="Havoc").run() == Result.OFFLINE


def test_useragents():
    flag = "ENOFLAG"
    checker = CheckerExampleImpl(method="StoreFlag", flag=flag)
    last_agent = checker.http_useragent
    new_agent = checker.http_useragent_randomize()
    assert checker.http_useragent == new_agent
    assert last_agent != checker.http_useragent


def main():
    pytest.main(sys.argv)


if __name__ == "__main__":
    main()