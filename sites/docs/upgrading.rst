.. _upgrading:

=========================
Upgrading from Fabric 1.x
=========================

Fabric 2 represents a near-total reimplementation & reorganization of the
software. It's been :ref:`broken in two <invoke-split-from-fabric>`, cleaned
up, made more explicit, and so forth. In some cases, upgrading requires only
basic search & replace; in others, more work is needed.

If you read this document carefully, it should guide you in the right direction
until you're fully upgraded. Should anything be missing, please file a ticket
`on Github <https://github.com/fabric/fabric>`_ and we'll update it ASAP.


Upgrading by not upgrading
==========================

We linked to a note about this above, but to be explicit: Fabric 2 is really
two separate libraries, and anything not strictly SSH or network related has
been :ref:`split out into the Invoke project <invoke-split-from-fabric>`.

This means that if you're in the group of users leveraging Fabric solely for
its task execution, and never used ``run()``, ``put()`` or similar - **you
don't need to use Fabric itself anymore** and can simply **'sidegrade' to using
Invoke instead**.

You'll still want to read over this document to get a sense of how things have
changed, but just be aware that you can get away with ``pip install invoke``
and won't need Fabric, Paramiko, cryptography dependencies, or anything else.


Why upgrade?
============

While this is not a replacement for the detailed lists later in the document,
we'd like to call out, in no particular order, some specific improvements in
Fabric 2 that might make it worth your time to make the jump.

.. note::
    These are all listed in the next section as well, so if you're already
    sold, just skip there.

- Python 3 compatibility (specifically, we now support 2.7 and 3.4+);
- Thread-safe - no more requirement on multiprocessing for concurrency;
- API reorganized around `.Connection` objects instead of global module state;
- Command-line parser overhauled to allow for regular GNU/POSIX style flags and
  options on a per-task basis (no more ``fab mytask:weird=custom,arg=format``);
- Task organization far more explicit and flexible / has far less 'magic';
- Tasks can declare other tasks to always be run before or after themselves;
- Configuration massively expanded to allow for multiple config files &
  formats, env vars, per-user/project/module configs, and much more;
- SSH config file loading enabled by default & has been fleshed out re:
  system/user/runtime file selection;
- Shell command execution API consistent across local and remote method calls -
  no more differentiation between ``local()`` and ``run()``;
- Shell commands significantly more flexible re: interactive behavior,
  simultaneous capture & display (now applies to local subprocesses, not just
  remote), and auto-responding;
- Improved flexibility in how Paramiko is used - `.Connection` allows for
  arbitrary control over the kwargs given to `SSHClient.connect
  <paramiko.client.SSHClient.connect>`;
- Gateway/jump-host functionality offers a ``ProxyJump`` style 'native' (no
  proxy-command subprocesses) option, which can be nested infinitely;


Upgrading piecemeal
===================

A quick note that Fabric 2 is being offered in two flavors to make gradual
upgrades less painful:

- As versions 2.0+ of the ``fabric`` package, which if installed, will replace
  Fabric 1 (aka versions 1.x of ``fabric``);
- And as the ``fabric2`` package, which is identical to the former in every
  way, save for the name exposed to Python's packaging and import systems.

Thus, if you have a large codebase and don't want to make the jump to 2.x in
one leap, it's possible to have both Fabric 1 (as ``fabric``, as you presumably
had it installed previously) and Fabric 2 (as ``fabric2``) resident in your
Python environment simultaneously.

.. note::
    We strongly recommend that you eventually migrate all code using Fabric 1,
    to version 2 or above, so that you can move back to installing and
    importing under the ``fabric`` name. ``fabric2`` as a distinct package and
    module is intended to be a stopgap, and there will not be any ``fabric3``
    or above.

For details on how to obtain the ``fabric2`` version of the package, see
:ref:`installing-as-fabric2`.


Example upgrade process
=======================

This section goes over upgrading a small but nontrivial Fabric 1 fabfile to
work with Fabric 2. It's not meant to be exhaustive, merely illustrative; for a
full list of how to upgrade individual features or concepts, see the last
section, :ref:`upgrade-specifics`.

Sample original fabfile
-----------------------

Here's a (slightly modified to concur with 'modern' Fabric 1 best practices)
copy of Fabric 1's final tutorial snippet, which we will use as our test case
for upgrading::

    from fabric.api import abort, env, local, run, settings, task
    from fabric.contrib.console import confirm

    env.hosts = ['my_server']

    @task
    def test():
        with settings(warn_only=True):
            result = local('./manage.py test my_app', capture=True)
        if result.failed and not confirm("Tests failed. Continue anyway?"):
            abort("Aborting at user request.")

    @task
    def commit():
        local("git add -p && git commit")

    @task
    def push():
        local("git push")

    @task
    def prepare_deploy():
        test()
        commit()
        push()

    @task
    def deploy():
        code_dir = '/srv/django/myproject'
        with settings(warn_only=True):
            if run("test -d {}".format(code_dir)).failed:
                cmd = "git clone user@vcshost:/path/to/repo/.git {}"
                run(cmd.format(code_dir))
        with cd(code_dir):
            run("git pull")
            run("touch app.wsgi")

We'll port this directly, meaning the result will still be ``fabfile.py``,
though we'd like to note that writing your code in a more library-oriented
fashion - even just as functions not wrapped in ``@task`` - can make testing
and reusing code easier.

Imports
-------

In this case, we don't need to import nearly as many functions, due to the
emphasis on object methods instead of global functions. We only need the
following:

- `sys`, for `sys.exit` (replacing ``abort()``);
- `@task <invoke.tasks.task>`, as before, but coming from Invoke as it's not
  SSH-specific;
- ``confirm``, which now comes from the Invocations library (also not
  SSH-specific, and Invocations is one of the descendants of
  ``fabric.contrib``, which no longer exists);

::

    import sys

    from invoke import task
    from invocations.console import confirm

Host list
---------

The idea of a global host lists is gone; there is currently no direct
replacement. Instead, we expect users to set up their own execution context,
creating explicit `.Connection` and/or `.Group` objects as needed, even if
that's simply by mocking v1's built-in "roles" map.

This is an area under active development, so feedback is welcomed.

For now, given the source snippet hardcoded a hostname of ``my_server``, we'll
assume this fabfile will be invoked as e.g. ``fab -H my_server taskname``, and
there will be no hardcoding within the fabfile itself.

.. TODO:
    - pre-task example
    - true baked-in default example (requires some sort of config hook)

Test task
---------

The first task in the fabfile uses a good spread of the API. We'll outline the
changes here (note that these are all listed above as well):

- Declaring a function as a task is nearly the same as before, but with an
  explicit initial context argument, whose value will be a `.Connection` object
  at runtime.
- The use of ``with settings(warn_only=True)`` can be replaced by a simple
  kwarg to the ``local()`` call.
- That ``local()`` call is now a method call on the `.Connection`,
  `.Connection.local`.
- ``capture`` is no longer a useful method; we can now capture and display at
  the same time, locally or remotely. If you don't actually *want* a local
  subprocess to mirror its stdout/err while it runs, you can simply say
  ``hide=True``.
- Result objects are pretty similar in v1 and v2; v2's no longer pretend to
  "be" strings, but instead act more like booleans, acting truthy if the
  command exited cleanly, and falsey otherwise. In terms of attributes
  exhibited, most of the same info is available, with v2 typically exposing
  more than v1.
- ``abort()`` is gone; you should use exceptions or builtins like ``sys.exit``
  instead.

.. TODO: check up on Fabric 2 compatible patchwork for confirm()

The result::

    @task
    def test(c):
        result = c.local('./manage.py test my_app', warn=True)
        if not result and not confirm("Tests failed. Continue anyway?"):
            sys.exit("Aborting at user request.")

Other simple tasks
------------------

The next two tasks are simple one-liners, and you've already seen what replaced
the global ``local()`` function::

    @task
    def commit(c):
        c.local("git add -p && git commit")

    @task
    def push(c):
        c.local("git push")

Calling tasks from other tasks
------------------------------

This is another area that is in flux at the Invoke level, but for now, we can
simply call the other tasks as functions, just as was done in v1. The main
difference is that we want to pass along our context object::

    @task
    def prepare_deploy(c):
        test(c)
        commit(c)
        push(c)

Actual remote steps
-------------------

Note that up to this point, nothing truly Fabric-related has been in play -
`.Connection.local` is just a rebinding of `Context.run
<invoke.context.Context.run>`, Invoke's local subprocess execution method. Now
we get to the actual deploy step, which simply invokes `.Connection.run`
instead, executing remotely (on whichever host the `.Connection` has been bound
to).

``with cd()`` is not yet implemented for the remote side of things, but we
expect it will be soon. For now we fall back to command chaining with ``&&``.

::

    @task
    def deploy(c):
        code_dir = '/srv/django/myproject'
        if not c.run("test -d {}".format(code_dir), warn=True):
            cmd = "git clone user@vcshost:/path/to/repo/.git {}"
            c.run(cmd.format(code_dir))
        c.run("cd {} && git pull".format(code_dir))
        c.run("cd {} && touch app.wsgi".format(code_dir))

The whole thing
---------------

Now we have the entire, upgraded fabfile that will work with Fabric 2::

    import sys

    from invoke import task
    from invocations.console import confirm

    @task
    def test(c):
        result = c.local('./manage.py test my_app', warn=True)
        if not result and not confirm("Tests failed. Continue anyway?"):
            sys.exit("Aborting at user request.")

    @task
    def commit(c):
        c.local("git add -p && git commit")

    @task
    def push(c):
        c.local("git push")

    @task
    def prepare_deploy(c):
        test(c)
        commit(c)
        push(c)

    @task
    def deploy(c):
        code_dir = '/srv/django/myproject'
        if not c.run("test -d {}".format(code_dir), warn=True):
            cmd = "git clone user@vcshost:/path/to/repo/.git {}"
            c.run(cmd.format(code_dir))
        c.run("cd {} && git pull".format(code_dir))
        c.run("cd {} && touch app.wsgi".format(code_dir))


.. _upgrade-specifics:

Upgrade specifics
=================

General / conceptual
--------------------

- All of Fabric 1's non-SSH-specific functionality (CLI parsing, task
  organization, command execution basics, etc) has been moved to a more general
  library called `Invoke <http://pyinvoke.org>`_. Fabric 2 builds on Invoke
  (and as before, on Paramiko) to present an SSH-specific API.

  .. warning::
    Please check Invoke's documentation before filing feature request tickets!

- Fabric 2 is fully Python 3 compatible; as a cost, Python 2.5 support has been
  dropped - in fact, we've dropped support for anything older than Python 2.7.
- The CLI task-oriented workflow remains a primary design goal, but the library
  use case is no longer a second-class citizen; instead, the library
  functionality has been designed first, with the CLI/task features built on
  top of it.
- Additionally, within the CLI use case, version 1 placed too much emphasis on
  'lazy' interactive prompts for authentication secrets or even connection
  parameters, driven in part by a lack of strong configuration mechanisms. Over
  time it became clear this wasn't worth the tradeoffs of confusing
  noninteractive behavior and difficult debugging or testing procedures.

  Version 2 takes an arguably cleaner approach (based on functionality added to
  v1 over time) where users are encouraged to leverage the configuration system
  and/or request prompts for runtime secrets at the start of the process; if
  the system determines it's missing information partway through, it raises
  exceptions instead of prompting.
- Invoke's design includes :ref:`explicit user-facing testing functionality
  <testing-user-code>`; if you didn't find a way to write tests for your
  Fabric-using code before, it should be much easier now.

    - We recommend trying to write tests early on; they will help clarify the
      upgrade process for you & also make the process safer!

API organization
----------------

- There's no longer a need to import everything through ``fabric.api``; all
  useful imports are now available at the top level, e.g. ``from fabric import
  Connection``.
- Speaking of: the primary API is now "instantiate `.Connection` objects and
  call their methods" instead of "manipulate global state and call module-level
  functions."
- Connections replace *host strings*, which are no longer first-order
  primitives but simply convenient, optional shorthand in a few spots (such as
  `.Connection` instantiation.)
- Connection objects store per-connection state such as user, hostname, gateway
  config, etc, and encapsulate low-level objects from Paramiko (such as their
  ``SSHClient`` instance.)

    - There is also a new ``connect_kwargs`` argument available in
      `.Connection` that takes arbitrary kwargs intended for the Paramiko-level
      ``connect()`` call; this means Fabric no longer needs explicit patches to
      support individual Paramiko features.

- Other configuration state (such as default desired behavior, authentication
  parameters, etc) can also be stored in these objects, and will affect how
  they operate. This configuration is also inherited from the CLI machinery
  when the latter is in use.
- The basic "respond to prompts" functionality found as Fabric 1's
  ``env.prompts`` dictionary option, has been significantly fleshed out into a
  framework of :ref:`Watchers <autoresponding>` which operate on a running
  command's input and output streams.

    - In addition, ``sudo`` has been rewritten to use that framework; while
      it's still useful to have implemented in Fabric (actually Invoke) itself,
      it doesn't use any private internals any longer.

- *Roles* (and other lists-of-host-strings such as the result of using ``-H``
  on the CLI) are now (or can be) implemented via `.Group` objects, which are
  lightweight wrappers around multiple Connections.
- v1's desire to tightly control program state (such as using ``abort()`` and
  ``warn()`` to exit and/or warn users) has been scaled back; instead you
  should simply use whatever methods you want in order to exit, log, and so
  forth.

    - For example, instead of ``abort("oh no!")``, you may just want to ``raise
      MyException("welp")`` or even ``sys.exit("Stuff broke!")``.

Tasks
-----

- Fabric-specific command-line tasks now take a `.Connection` object as their
  first positional argument.

    - This sacrifices some of the "quick DSL" of v1 in exchange for a
      significantly cleaner, easier to understand/debug, and more
      user-overrideable, API structure.
    - It also lessens the distinction between "a module of functions" and "a
      class of methods"; users can more easily start with the former and
      migrate to the latter when their needs grow/change.

- Old-style task functions (those not decorated with ``@task``) are gone. You
  must now always use ``@task``. (Note that users heavily attached to old-style
  tasks should be able to reimplement them by extending
  `~invoke.collection.Collection`!)
- Task organization is much more explicit; instead of crawling imports, the
  system expects you to declare a root 'namespace' task collection which is
  composed of tasks and/or sub-collections.

    - A simple single top-level ``tasks.py`` can remain a "pile of tasks",
      without requiring a namespace, but any deeper organization must be done
      explicitly.)

- Tasks can declare "pre-tasks" and "post-tasks" that behave a lot like
  Makefile target dependencies; e.g. you can now state that a given task
  requires another to be run prior to itself anytime it is invoked.
- Nearly all task-related functionality is implemented in Invoke; for more
  details see its :ref:`execution <task-execution>` and :ref:`namespaces
  <task-namespaces>` documentation.

CLI arguments and options
-------------------------

- ``-I``/``--initial-password-prompt`` is now :option:`--prompt-for-password`
  and/or :option:`--prompt-for-passphrase`, depending on whether you were using
  the former to fill in passwords or key passphrases (or both.)
- ``-a``/``--no_agent`` has not been ported over from v1, since OpenSSH lacks a
  similar CLI option. We may add it back in the future; for now, unset
  ``SSH_AUTH_SOCK`` in the hosting shell environment or configure
  ``connect_kwargs.allow_agent`` to be ``False``.
- TODO: rest of this

General shell commands
----------------------

- All shell command execution is now unified; in v1, ``local()`` and
  ``run()``/``sudo()`` had significantly different signatures and behavior, but
  in v2 they all use the same underlying protocol and logic, with only details
  like process creation and pipe consumption differing.
- Thus, where ``local()`` required you to choose between displaying and
  capturing program output, that dichotomy no longer exists; both local and
  remote execution always captures, and either may conditionally show or hide
  stdout or stderr while the program runs.

Remote shell commands
---------------------

- There is no more built-in ``use_shell`` or ``shell`` option; the old "need"
  to wrap with an explicit shell invocation is no longer necessary or usually
  desirable. TODO: this isn't 100% true actually, it depends :(

Networking
----------

- ``env.gateway`` is now the ``gateway`` kwarg to `.Connection`, and -- for
  ``ProxyJump`` style gateways -- should be another `.Connection` object
  instead of a host string.

    - You may specify a runtime, non-SSH-config-driven ``ProxyCommand``-style
      string as the ``gateway`` kwarg instead, which will act just like a
      regular ``ProxyCommand``.
    - SSH-config-driven ``ProxyCommand`` continues to work as it did in v1.
    - ``ProxyJump``-style gateways (using nested/inner `.Connection` objects)
      may be nested indefinitely, as you might expect.

- ``fabric.context_managers.remote_tunnel`` (which forwards a locally
  visible/open port to the remote end so remote processes may connect to it) is
  now `.Connection.forward_local`.
- Accompanying `.Connection.forward_local` is the logical inversion,
  `.Connection.forward_remote` (forwards a remotely visible port locally),
  which is new in Fabric 2 and was not implemented in Fabric 1 at time of
  writing (though there are patches for it).

Authentication
--------------

- Most ``env`` keys from v1 were simply passthroughs to Paramiko's
  ``connect()`` method, and thus in v2 should be set in the ``connect_kwargs``
  :doc:`configuration </concepts/configuration>` tree:

    - ``gss_auth``, ``gss_deleg`` and ``gss_kex``
    - ``key_filename``
    - ``password`` (v1 used this for both sudo and connection-level passwords;
      in v2 it is *only* used to fill in ``connect()``. Paramiko itself (in
      versions 1.x and 2.x) uses this value for both password auth and key
      decryption.

- Some other ``env`` keys that aren't direct passthroughs:

    - ``key``: was used to automatically instantiate one of a couple `PKey
      <paramiko.pkey.PKey>` subclasses and hand the result to ``connect()``'s
      ``pkey`` kwarg. This has been dropped; users should themselves know which
      type of key they're dealing with and instantiate a ``PKey`` subclass
      themselves, and place the result in ``connect_kwargs.pkey``.
    - ``no_agent``: this was simply a renaming/inversion of the ``allow_agent``
      kwarg to ``connect()``. Users who were setting this to ``True`` should
      now simply set ``connect_kwargs.allow_agent`` to ``False``.
    - ``no_keys``: similar to ``no_agent``, this was just an inversion of
      ``look_for_keys``, so migrate to using ``connect_kwargs.look_for_keys``
      instead.
    - ``passwords``: has been moved into :ref:`host-configuration`.

- ``IdentityFile`` (via :ref:`ssh_config <ssh-config>` files) is honored in v2,
  same as it was in v1.

Configuration
-------------

- General configuration has been massively improved over the old ``fabricrc``
  files; Fabric 2 builds on Invoke which offers a full-fledged configuration
  hierarchy (in-code config, multiple config file locations, environment
  variables, CLI flags, and more) and multiple file formats.

    - Anytime you used to modify Fabric's config by manipulating
      ``fabric.(api.)env`` (or using ``with settings():``), you will now be
      using Invoke-style config manipulation and/or method keyword arguments.
    - See :ref:`Invoke's configuration documentation <configuration>` for
      details on how the system works, where config sources come from, etc; and
      for non-SSH-specific settings, such as whether to hide command output.
    - See :ref:`Fabric's specific config doc page <fab-configuration>` for the
      modifications & additions Fabric makes in this area, such as SSH-specific
      settings like default port number or whether to forward an SSH agent.

- :ref:`SSH config file loading <ssh-config>` has also improved. Fabric 1
  allowed selecting a single SSH config file; version 2 behaves more like
  OpenSSH and will seek out both system and user level config files, as well as
  allowing a runtime config file. (And advanced users may simply supply their
  own Paramiko SSH config object they obtained however.)
- Speaking of SSH config loading, it is **now enabled by default**, and may be
  easily :ref:`disabled <disabling-ssh-config>` by advanced users seeking
  purity of state.
- On top of the various SSH config directives implemented in v1, v2 honors
  ``ConnectTimeout`` and ``ProxyJump``; generally, the intention is now that
  SSH config support is to be included in any new feature added, when
  appropriate.
