# Mockup | A platform-independent C/C++ deploy tool

Easily mock up your C/C++ programs into platform-independent, self-contained executable files. No more GLIBC version pains.

> See that little file `mockup.py` in this repo? Download it. End of your hell Linux deployment experiences.

## Mocking dependencies 😏

Have you annoyed sucking the stupid `GLIBC_xxx symbol not found` errors when trying to copy your locally-compiled programs to your boss's way-too-old CentOS servers?

Annoyed 'It works on my Ubuntu 24.04!' but failed to start on customer's ancient Ubuntu 18.04?

This tool fucks them up. 😤

Compiled on your local computer, runs on any Linux distributions, forever. 😎

It runs on your boss's stupid 'Enterprice' CentOS just like on your local fancy Arch Linux!

Feel free to use all fancy C++23 cutting edge features, use any dedicated fancy libraries you locally have.

`mockup` can automatically detect and copies all dependencies (including libstdc++!) all together with your executable file!

Stupid `libxxx.so not found`, `GLIBC_xxx not found` errors no more.

Enjoy C++23 programming even if targeting poorest CentOS 7 platform.

## Difference to linuxdeployqt?

Unlike other Linux deploy tools that only copies dependent library files, `mockup` also ship `libc.so` and `libstdc++.so` standard libraries.

> Actually, `mockup` will ship the `ld-linux-x86-64.so.2` as well, to ensure 100% compatbility to all Linux distros, as long as it runs on x86-64.

Tools like `linuxdeployqt` only copies external dependencies like `libQtCore.so` and `libtbb.so` still requires you to build the whole program on a very ancient platform like CentOS 7 to ensure enough coverage over most newer Linux distros, thus still under `GLIBCXX symbol not found` curse. This heavily limits the version of gcc toolchain (therefore limits the C++ feature you can use).

While `mockup` doesn't, you can build your program on Ubuntu 24.04 or Arch Linux, and still work on all Linux distros.

Compile anywhere, runs anywhere! Allowing a wider toolchain / C++ standard choice as long as available locally on your develop environment.

## Usage ✨

For example, you compiled a program named `my_app` locally on your Arch Linux (with very new GLIBC version). And it used latest C++20 features, depends on several fancy `.so` libraries dependencies.

And you need to deploy this program to a very ancient Linux distribution: CentOS, which have very old GLIBC version, totally doesn't support C++20 at all...

If you simply copy the `my_app` to the target CentOS machine, it won't run at all. Maybe report `libxxx.so not found`, or `GLIBCXX_2.43 version not found in libstdc++.so`.

This tool `mockup` is to solve all these pains.

Just run this on your local machine:

```bash
python mockup.py ./my_app -o my_app_packaged
tar zcvf my_app_pacakged.tgz my_app_packaged
```

Now deploy the `my_app_packaged.tgz` to your target customer machine.

And on target machine you run:

```bash
tar zxvf my_app_pacakged.tgz my_app_packaged
my_app_packaged/my_app.sh
```

## Explain 🕷️

The directory `my_app_packaged` should contains `my_app` and all it's dependencies:

```
$ ls my_app_packaged
my_app  my_app.sh  ld-linux-x86-64.so.2  libc.so.6
libtbb.so.12  libgcc_s.so.1  libm.so.6  libstdc++.so.6
```

`my_app` is your original program. Itself cannot be executed on the target machine directly.

We must run `my_app.sh` instead, this is a mocked shell file by our tool, it can correctly start the with `$LD_LIBRARY_PATH` environment stuffs set up correctly.

## Mocks even better? 💌

It's also recommended to install `patchelf` to enable `-P` option for our `mockup` tool.

```bash
sudo apt install patchelf
python mockup.py ./my_app -P -o my_app_packaged
```

When `-P` option is on, `mockup` will use `patchelf` to modify your `my_app` and it's dependent libraries to force them to look up in the `my_app_packaged` (with the power of `$ORIGIN` syntax of RPATH), so that `$LD_LIBRARY_PATH` environment variable is no longer required, allowing `my_app` to invoke target machines local executables (like invoking `/bin/ls` with `system()`) without library conflict errors.

Run `python mockup.py -h` for more usage helps.

## Still don't believe?

Goto [Release page](https://github.com/archibate/mockup/releases/tag/cpp23test), download the `cpp23test.tgz` there.

It's a simple test C++ program `cpp23` compiled on my latest Arch Linux, used a fancy C++23 feature. Source code can be found [here](example).

I packed it with the `mockup` tool. It should now runs correctly on your whatever Linux distro, with or without C++23 libstdc++ in system environment.

```bash
wget https://github.com/archibate/mockup/releases/download/cpp23test/cpp23test.tgz
tar zxvf cpp23test.tgz
cd cpp23test
./cpp23.sh  # prints "Hello from C++23".
./cpp23     # should also works, since I used the -P option.
```

## Limitations 🥺

- Linux executables only, didn't work on Windows / MacOS for now.
- Can't deploy x86-64 executables to ARM target systems, of course.

## Issues?

Let me know if you have any problems or feature requests about this tiny tool by sending [GitHub issues](https://github.com/archibate/mockup/issues).
