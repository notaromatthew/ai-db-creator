// Contratto: lo implementa chi si occupa di dashboard/condivisione. ProjectPage lo usa cosi':
//   <ShareDialog projectId={id} open={shareOpen} onClose={() => setShareOpen(false)} />
export default function ShareDialog(_props: { projectId: string; open: boolean; onClose: () => void }) {
  return null
}
