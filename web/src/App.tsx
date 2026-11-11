import { MotionConfig } from "motion/react"
import { DocNAApp } from "@/pages/DocNAApp"
import "./index.css"

function App() {
  return (
    <MotionConfig reducedMotion="user">
      <DocNAApp />
    </MotionConfig>
  )
}

export default App
