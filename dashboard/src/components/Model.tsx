import { Canvas } from "@react-three/fiber";
import { useRef, useLayoutEffect, useMemo } from "react";
import { OrbitControls, useGLTF, Environment } from "@react-three/drei";
import * as THREE from "three";
import { Perf } from "r3f-perf";

export default function Model({ url = "../assets/classroom.glb", twin }: any) {
  return (
    <>
      <Canvas camera={{ position: [0, 5, 10], fov: 50 }}>
        <ambientLight intensity={1} />
        <directionalLight position={[10, 10, 10]} intensity={2} />
        <Environment preset="city" />

        <Perf position="top-right" />

        <ModelView url={url} twin={twin} />
        <OrbitControls />
      </Canvas>
    </>
  );
}
export const ModelView = ({ url, twin }: any) => {
  const model: any = useGLTF(url);
  const { scene, nodes }: any = model;

  const isSeatEmpty = (seat: any) => {
    if (!seat) return true;
    if (seat.attendance_status || seat.is_occupied) return false;
    return true;
  };

  const getSeatColor = (seat: any) => {
    if (!seat) return "#ffffff"; // white
    if (seat.attendance_status === "present") return "#4caf50"; // green
    if (seat.attendance_status === "rejected") return "#f44336"; // red
    if (seat.attendance_status === "revoked") return "#ff9800"; // orange
    if (seat.is_occupied) return "#9e9e9e"; // grey
    return "#e0e0e0"; // light grey for empty
  };

  const spacingX = 1.5;
  const spacingZ = 1.5;

  // Optional: Hide the default single chair from the scene if it exists
  if (nodes.Chair) {
    nodes.Chair.visible = false;
  }

  return (
    <group>
      <mesh rotation={[0, Math.PI, 0]} position={[0, 0.8, 0]}>
        <primitive object={scene} />
      </mesh>

      {/* 3D Seat Grid */}
      {twin && twin.seats && (
        <group position={[0, 1.5, 0]}>
          {twin.seats.map((seat: any) => {
            // Calculate centered position
            const offsetX = (twin.layout_cols * spacingX) / 2;
            const offsetZ = (twin.layout_rows * spacingZ) / 2;
            const x = seat.col * spacingX - offsetX + spacingX / 2;
            const z = seat.row * spacingZ - offsetZ + spacingZ / 2;

            const empty = isSeatEmpty(seat);

            return (
              <mesh
                key={seat.seat_id}
                geometry={nodes.Chair.geometry}
                material={empty ? nodes.Chair.material : undefined}
                position={[x, 0, z]}
                rotation={[0, 0, 0]}
              >
                {!empty && <meshStandardMaterial color={getSeatColor(seat)} />}
              </mesh>
            );
          })}
        </group>
      )}
    </group>
  );
};
