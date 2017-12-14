from invoke import Call, Executor, Task
from invoke.util import debug

from . import Connection
from .exceptions import NothingToDo


# TODO: come up w/ a better name heh
class FabExecutor(Executor):
    def expand_calls(self, calls):
        # Generate new call list with per-host variants & Connections inserted
        ret = []
        # TODO: mesh well with Invoke list-type args helper (inv #132)
        hosts = self.core[0].args.hosts.value
        hosts = hosts.split(',') if hosts else []
        for call in calls:
            # TODO: roles, other non-runtime host parameterizations, etc
            for host in hosts:
                # TODO: handle pre/post, which we are currently ignoring,
                # because it's poorly defined right now: does each
                # parameterized per-host task run its own pre/posts, or do they
                # run before/after the 'set' of per-host tasks? and etc
                # TODO: tie into whatever DAG stuff we do in Invoke; ideally
                # this all gets pushed down to that level and we simply hand in
                # the raw 'one of these each with host=a, host=b, ... plz'
                ret.append(self.parameterize(call, host))
            # Deal with lack of hosts arg (acts same as `inv` in that case)
            # TODO: no tests for this branch?
            if not hosts:
                ret.append(call)
        # Add remainder as anonymous task
        if self.core.remainder:
            # TODO: this will need to change once there are more options for
            # setting host lists besides "-H or 100% within-task"
            if not hosts:
                raise NothingToDo("Was told to run a command, but not given any hosts to run it on!") # noqa
            def anonymous(c):
                # TODO: how to make all our tests configure in_stream=False?
                c.run(self.core.remainder, in_stream=False)
            anon = Call(Task(body=anonymous))
            # TODO: see above TODOs about non-parameterized setups, roles etc
            # TODO: will likely need to refactor that logic some more so it can
            # be used both there and here.
            for host in hosts:
                ret.append(self.parameterize(anon, host))
        return ret

    def parameterize(self, call, host):
        """
        Parameterize a Call with its Context set to a per-host Config.
        """
        debug("Parameterizing {0!r} for host {1!r}".format(call, host))
        # Generate a custom ConnectionCall that knows how to yield a Connection
        # in its make_context(), specifically one to the host requested here.
        clone = call.clone(into=ConnectionCall)
        # TODO: using bag-of-attrs is mildly gross but whatever, I'll take it.
        clone.host = host
        return clone

    def dedupe(self, tasks):
        # Don't perform deduping, we will often have "duplicate" tasks w/
        # distinct host values/etc.
        # TODO: might want some deduplication later on though - falls under
        # "how to mesh parameterization with pre/post/etc deduping".
        return tasks


class ConnectionCall(Call):
    """
    Subclass of `invoke.tasks.Call` that generates `Connections <.Connection>`.
    """
    def make_context(self, config):
        return Connection(host=self.host, config=config)
