%{?scl:%scl_package rubygem-%{gem_name}}
%{!?scl:%global pkg_name %{name}}

# Enable test. This includes RSpec into sources.
%bcond_with tests

# Generated from mysql2-0.3.11.gem by gem2rpm -*- rpm-spec -*-
%global gem_name mysql2

Name: %{?scl_prefix}rubygem-%{gem_name}
Version: 0.5.3
Release: 2%{?dist}
Summary: A simple, fast Mysql library for Ruby, binding to libmysql
License: MIT
URL: https://github.com/brianmario/mysql2
Source0: https://rubygems.org/gems/%{gem_name}-%{version}.gem
# git clone --no-checkout https://github.com/brianmario/mysql2.git
# cd mysql2 && git archive -v -o mysql2-0.5.3-tests.txz 0.5.3 spec/
Source1: %{gem_name}-%{version}-tests.txz
# Sources of RSpec for interanl tests. Don't import these.
%if %{with tests}
Source200: https://rubygems.org/gems/diff-lcs-1.3.gem
Source201: https://rubygems.org/gems/rspec-3.7.0.gem
Source202: https://rubygems.org/gems/rspec-core-3.7.0.gem
Source203: https://rubygems.org/gems/rspec-expectations-3.7.0.gem
Source204: https://rubygems.org/gems/rspec-mocks-3.7.0.gem
Source205: https://rubygems.org/gems/rspec-support-3.7.0.gem
%endif
# Fix a client option local_infile not enabled
# with mariadb-connector-c on big endian environment.
# We still needs this patch.
# https://github.com/brianmario/mysql2/pull/914
# https://github.com/MariaDB/mariadb-connector-c/commit/434b67e
Patch0: rubygem-mysql2-0.4.10-mariadb-connector-c-3.0.2-fix-wrong-local-infile-on-big-endian.patch

# Required in lib/mysql2.rb
Requires: %{?scl_prefix}rubygem(bigdecimal)
BuildRequires: %{?scl_prefix}ruby(release)
BuildRequires: %{?scl_prefix}rubygems-devel
BuildRequires: %{?scl_prefix}ruby-devel
BuildRequires: gcc
BuildRequires: mariadb-devel
%if %{with tests}
BuildRequires: mariadb-server
# Used in mysql_install_db
BuildRequires: hostname
BuildRequires: %{?scl_prefix}rubygem(bigdecimal)
# Used in spec/em/em_spec.rb
#BuildRequires: %%{?scl_prefix}rubygem(eventmachine)
%endif
Provides: %{?scl_prefix}rubygem(%{gem_name}) = %{version}

%description
The Mysql2 gem is meant to serve the extremely common use-case of
connecting, querying and iterating on results. Some database libraries
out there serve as direct 1:1 mappings of the already complex C API\'s
available. This one is not.


%package doc
Summary: Documentation for %{pkg_name}
Requires: %{?scl_prefix}%{pkg_name} = %{version}-%{release}
BuildArch: noarch

%description doc
Documentation for %{pkg_name}

%prep
%{?scl:scl enable %{scl} - << \EOF}
set -ex
gem unpack %{SOURCE0}

%setup -q -D -T -n  %{gem_name}-%{version} -b 1

%patch0 -p1

gem spec %{SOURCE0} -l --ruby > %{gem_name}.gemspec
%{?scl:EOF}

%build
%{?scl:scl enable %{scl} - << \EOF}
set -ex
# Create the gem as gem install only works on a gem file
gem build %{gem_name}.gemspec

# %%gem_install compiles any C extensions and installs the gem into ./%%gem_dir
# by default, so that we can move it into the buildroot in %%install
%gem_install
%{?scl:EOF}


%install
mkdir -p %{buildroot}%{gem_dir}
cp -pa .%{gem_dir}/* \
        %{buildroot}%{gem_dir}/

mkdir -p %{buildroot}%{gem_extdir_mri}
cp -a .%{gem_extdir_mri}/* %{buildroot}%{gem_extdir_mri}/

# Prevent dangling symlink in -debuginfo.
rm -rf %{buildroot}%{gem_instdir}/ext


%if %{with tests}
%check
%{?scl:scl enable %{scl} - << \EOF}
set -ex
pushd .%{gem_instdir}
# Move the tests into place
ln -s %{_builddir}/spec spec

pushd %{_sourcedir}
gem install rspec*.gem --local --no-document
popd
# Export path with locally installed rspec executable.
export PATH="~/bin:${PATH}"

TOP_DIR=$(pwd)
# Use testing port because the standard mysqld port 3306 is occupied.
# Assign a random port to consider a case of multi builds in parallel in a host.
# https://src.fedoraproject.org/rpms/rubygem-pg/pull-request/3
MYSQL_TEST_PORT="$((13306 + ${RANDOM} % 1000))"
MYSQL_TEST_USER=$(id -un)
MYSQL_TEST_DATA_DIR="${TOP_DIR}/data"
MYSQL_TEST_SOCKET="${TOP_DIR}/mysql.sock"
MYSQL_TEST_LOG="${TOP_DIR}/mysql.log"
MYSQL_TEST_PID_FILE="${TOP_DIR}/mysql.pid"

mkdir "${MYSQL_TEST_DATA_DIR}"
# Add the basedir option to avoid an error on mariadb <= 5.5.64.
# https://bugzilla.redhat.com/show_bug.cgi?id=1763343
mysql_install_db \
  --datadir="${MYSQL_TEST_DATA_DIR}" \
  --log-error="${MYSQL_TEST_LOG}" \
  --basedir=/usr

%{?_root_libexecdir}%{!?_root_libexecdir:%{_libexecdir}}/mysqld \
  --datadir="${MYSQL_TEST_DATA_DIR}" \
  --log-error="${MYSQL_TEST_LOG}" \
  --socket="${MYSQL_TEST_SOCKET}" \
  --pid-file="${MYSQL_TEST_PID_FILE}" \
  --port="${MYSQL_TEST_PORT}" \
  --ssl &

for i in $(seq 10); do
  sleep 1
  if grep -q 'ready for connections.' "${MYSQL_TEST_LOG}"; then
    break
  fi
  echo "Waiting connections... ${i}"
done

# See https://github.com/brianmario/mysql2/blob/master/.travis_setup.sh
mysql -u root \
  -e 'DROP DATABASE test; CREATE DATABASE /*M!50701 IF NOT EXISTS */ test' \
  -S "${MYSQL_TEST_SOCKET}" \
  -P "${MYSQL_TEST_PORT}"

# See https://github.com/brianmario/mysql2/blob/master/tasks/rspec.rake
cat <<EOS > spec/configuration.yml
root:
  host: localhost
  username: root
  password:
  database: test
  port: ${MYSQL_TEST_PORT}
  socket: ${MYSQL_TEST_SOCKET}

user:
  host: localhost
  username: ${MYSQL_TEST_USER}
  password:
  database: mysql2_test
  port: ${MYSQL_TEST_PORT}
  socket: ${MYSQL_TEST_SOCKET}
EOS

# This test would require changes in host configuration.
sed -i '/^  it "should be able to connect via SSL options" do$/,/^  end$/ s/^/#/' \
  spec/mysql2/client_spec.rb

# performance_schema.session_account_connect_attrs is unexpectedly empty.
# https://github.com/brianmario/mysql2/issues/965
sed -i '/^  it "should set default program_name in connect_attrs" do$/,/^  end$/ s/^/#/' \
  spec/mysql2/client_spec.rb
sed -i '/^  it "should set custom connect_attrs" do$/,/^  end$/ s/^/#/' \
  spec/mysql2/client_spec.rb

# TODO Fix this SCL specific issue.
sed -i '/^    it "should raise an exception if streaming ended due to a timeout" do$/,/^    end$/ s/^/#/' \
  spec/mysql2/result_spec.rb

rspec -Ilib:%{buildroot}%{gem_extdir_mri} -f d spec
popd

# Clean up
MYSQL_TEST_PID=$(cat "${MYSQL_TEST_PID_FILE}")
kill "${MYSQL_TEST_PID}"
# Kill target process completely to avoid error on Copr.
# http://post-office.corp.redhat.com/archives/internal-copr/2017-December/msg00001.html
for i in $(seq 10); do
  sleep 1
  if ! kill -0 "${MYSQL_TEST_PID}"; then
    break
  fi
  echo "Killing the mysql process... ${i}"
done

%{?scl:EOF}
%endif

%files
%dir %{gem_instdir}
%{gem_libdir}
%{gem_extdir_mri}
%exclude %{gem_cache}
%{gem_spec}
%exclude %{gem_instdir}/support
%license %{gem_instdir}/LICENSE

%files doc
%doc %{gem_docdir}
%doc %{gem_instdir}/README.md
%doc %{gem_instdir}/CHANGELOG.md


%changelog
* Wed Jan 27 2021 Jun Aruga <jaruga@redhat.com> - 0.5.3-2
- Add the basedir option to mysql_install_db to avoid an error on mariadb <= 5.5.64.
  Resolves: rhbz#1903661

* Thu Dec 19 2019 Jun Aruga <jaruga@redhat.com> - 0.5.3-1
- New upstream release 0.5.3

* Thu Jul 19 2018 Jun Aruga <jaruga@redhat.com> - 0.5.2-1
- New upstream release 0.5.2

* Mon Feb 26 2018 Jun Aruga <jaruga@redhat.com> - 0.4.10-3
- Rebuilt for fixed ruby document generation issue.

* Fri Jan 05 2018 Jun Aruga <jaruga@redhat.com> - 0.4.10-2
- New upstream release 0.4.10

* Thu Aug 03 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.4.8-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Thu Jul 27 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.4.8-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Thu Jul 13 2017 Adam Williamson <awilliam@redhat.com> - 0.4.8-1
- New upstream release 0.4.8 (builds against MariaDB 10.2)

* Sat Feb 11 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.4.4-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Wed Jan 11 2017 Vít Ondruch <vondruch@redhat.com> - 0.4.4-2
- Rebuilt for https://fedoraproject.org/wiki/Changes/Ruby_2.4

* Thu Jun 09 2016 Miroslav Suchý <msuchy@redhat.com> - 0.4.4-1
- New upstream release 0.4.4

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 0.4.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Mon Jan 11 2016 Vít Ondruch <vondruch@redhat.com> - 0.4.0-2
- Rebuilt for https://fedoraproject.org/wiki/Changes/Ruby_2.3

* Tue Sep  8 2015 Miroslav Suchý <msuchy@redhat.com> 0.4.0-1
- rebase to mysql2-0.4.0

* Thu Jun 18 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.16-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Fri Jan 16 2015 Vít Ondruch <vondruch@redhat.com> - 0.3.16-4
- Rebuilt for https://fedoraproject.org/wiki/Changes/Ruby_2.2

* Mon Aug 18 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.16-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Sun Jun 08 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.3.16-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Mon May 26 2014 Miroslav Suchý <msuchy@redhat.com> 0.3.16-1
- rebase to mysql2-0.3.16

* Tue Apr 15 2014 Vít Ondruch <vondruch@redhat.com> - 0.3.15-3
- Rebuilt for https://fedoraproject.org/wiki/Changes/Ruby_2.1

* Tue Feb 11 2014 Miroslav Suchý <msuchy@redhat.com> 0.3.15-2
- rebase to mysql2-0.3.15

* Wed Sep 11 2013 Alexander Chernyakhovsky <achernya@mit.edu> - 0.3.13-1
- Initial package
