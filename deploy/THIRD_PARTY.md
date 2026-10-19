# Third-party notices for the collaborator images

Checked on 2026-10-19 from the upstream project pages and the Gazebo Fuel API.
The public images install ROS packages from apt. They do not contain a Fuel
cache, a Fields2Cover wheel, or a copy of the owner's laptop fuel-cache tarball.

## Allowed inside the published images

| Piece | How it gets in | Terms | What we keep |
|---|---|---|---|
| ROS 2 Humble and Gazebo Fortress | apt from `packages.ros.org` and Ubuntu jammy | ROS 2 and Gazebo Fortress are Apache-2.0. Individual Ubuntu library packages keep their own licenses. | Installed as distribution packages. Source is the public apt repositories. |
| `ros-humble-foxglove-bridge` | `apt download` in `src/lab/ros/native/install-ros-extras.sh`, unpacked under the image's runtime prefix | MIT. Source: https://github.com/foxglove/ros-foxglove-bridge | Copyright and the MIT notice stay with the unpacked package. The image does not strip license files out of the deb. |
| `ros-humble-rosx-introspection` | same apt unpack | MPL-2.0. Source: https://github.com/facontidavide/rosx_introspection | The deb is redistributable when this notice and the public source offer stay available. License files from the package are not removed. |

## Not in the images and not in public Releases

| Piece | Terms seen on 2026-10-19 | Decision |
|---|---|---|
| OpenRobotics Warehouse, version 5 | CC BY-NC-ND 4.0 | Do not redistribute. A user may download it from https://fuel.gazebosim.org with `urp fuel`. |
| MovAi shelf_big, version 2 | CC BY-NC-ND 4.0 | Do not redistribute. |
| MovAi shelf, version 1 | CC BY-NC 4.0 | Do not put it in an unrestricted public image or Release. |
| OpenRobotics Depot 6, Chair 3, foldable_chair 3, MaleVisitorOnPhone 2 | CC BY 4.0 | Redistribution would require attribution. They are not baked in. The warehouse world is incomplete without the NC/ND models, so a partial CC BY set is not shipped either. |
| OpenRobotics Table 4, Jersey Barrier 6; plateau Casual female 1 | CC0 1.0 | Redistribution is allowed. They are still not baked in, because they do not make warehouse or depot runnable by themselves. |
| Fields2Cover 2.1.0 wheel `fields2cover-2.1.0-cp312-cp312-linux_x86_64.whl` | BSD-3-Clause. Source: https://github.com/Fields2Cover/Fields2Cover | The wheel is not in git and not in the image. The owner may upload it with `deploy/upload-assets.sh` only together with this notice and the BSD copyright and disclaimer. SHA256 `0fe53e459024b282be455b2a4bdbca3d93efa029539ff87c88c1105361344c19`. |

`maze` starts with the TurtleBot4 world that apt installs. It does not need Fuel.

The owner's snapshot `fuel-cache.tar.zst` (SHA256 `ee2d2ce72dea345b5aaac8c4fe0d3d501a8d51c3211ba1c038ca025cc0ae3b0d`) mixes the models above. Do not publish that tarball.
