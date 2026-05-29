import TimeAgo from "react-timeago";
import { format } from "date-fns";

export const DateTimeField = ({ date }: { date: Date }) => {
  const formatString = "dd MMM yy, HH:mm.ss 'UTC'";
  if (!date || isNaN(date.getTime())) {
    return <div><p className="text-gray-400">—</p></div>;
  }
  return (
    <div>
      <p className="">
        <TimeAgo date={date} />
      </p>
      <p className="text-gray-500 text-xs">
        {format(new Date(date), formatString)}
      </p>
    </div>
  );
};
