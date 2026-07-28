export async function GET() {
  return Response.json(
    { status: "healthy", service: "renewableops-dashboard" },
    {
      status: 200,
      headers: { "Cache-Control": "no-store" },
    },
  );
}
