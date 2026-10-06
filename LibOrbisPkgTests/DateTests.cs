using Microsoft.VisualStudio.TestTools.UnitTesting;
using System;
using LibOrbisPkg.GP4;
using LibOrbisPkg.PKG;

namespace LibOrbisPkgTests
{
  /// <summary>
  /// GP4 dates are written without a zone and are UTC. These only fail on a machine whose local
  /// zone is not UTC (CI usually is UTC), e.g. run with TZ=Europe/Sofia.
  /// </summary>
  [TestClass]
  public class DateTests
  {
    [TestMethod]
    public void VolumeTimestamp_RoundTripsUnchanged()
    {
      var ts = new DateTime(2022, 1, 21, 7, 9, 3, DateTimeKind.Utc);
      var vol = new Volume { TimeStamp = ts };
      Assert.AreEqual(ts, vol.TimeStamp.ToUniversalTime());
      Assert.AreEqual("2022-01-21 07:09:03", vol.volume_ts);
    }

    [TestMethod]
    public void CreationDate_DateOnly_KeepsTheDay()
    {
      var proj = Gp4Project.Create(VolumeType.pkg_ps4_app);
      proj.volume.Package.CreationDate = "2021-08-03";
      var props = PkgProperties.FromGp4(proj, ".");
      Assert.AreEqual("20210803", props.CreationDate.ToString("yyyyMMdd"));
      Assert.IsFalse(props.UseCreationTime);
    }

    [TestMethod]
    public void CreationDate_WithTime_KeepsDateAndTime()
    {
      var proj = Gp4Project.Create(VolumeType.pkg_ps4_app);
      proj.volume.Package.CreationDate = "2022-01-21 08:09:03";
      var props = PkgProperties.FromGp4(proj, ".");
      Assert.AreEqual("20220121 080903", props.CreationDate.ToString("yyyyMMdd HHmmss"));
      Assert.IsTrue(props.UseCreationTime);
    }
  }
}
